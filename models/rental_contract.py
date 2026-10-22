import logging
import requests
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class RentalHouse(models.Model):
    _name = 'rental.house'
    _description = 'Master Unit Rumah Sewa'

    name = fields.Char(string='Nama / Nomor Rumah', required=True)
    house_type = fields.Selection([
        ('t36', 'Tipe 36'),
        ('t45', 'Tipe 45'),
        ('t70', 'Tipe 70'),
        ('kios', 'Kios / Ruko')
    ], string='Tipe Rumah', required=True)
    address = fields.Text(string='Alamat Lengkap')
    status = fields.Selection([
        ('available', 'Tersedia (Kosong)'),
        ('rented', 'Tersewa')
    ], string='Status Rumah', default='available', readonly=True)


class RentalContract(models.Model):
    _name = 'rental.contract'
    _description = 'Kontrak Sewa Rumah'
    _order = 'due_date asc, id desc'

    name = fields.Char(string='Kode Kontrak', required=True, copy=False, readonly=True, default='New')
    tenant_name = fields.Char(string='Nama Penyewa', required=True)
    tenant_phone = fields.Char(string='No. WhatsApp (contoh: 62812xxx)', required=True)
    
    house_id = fields.Many2one('rental.house', string='Unit Rumah', required=True, domain="[('status', '=', 'available')]")
    house_type = fields.Selection(related='house_id.house_type', string='Tipe Rumah', store=True)
    
    payment_scheme = fields.Selection([
        ('monthly', 'Perbulan'),
        ('yearly', 'Pertahun')
    ], string='Skema Cicilan', default='monthly', required=True)
    
    start_date = fields.Date(string='Tanggal Masuk', default=fields.Date.today, required=True)
    due_date = fields.Date(string='Tanggal Jatuh Tempo', required=True)
    amount = fields.Float(string='Nominal Cicilan/Sewa', required=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Berjalan'),
        ('overdue', 'Jatuh Tempo (H+1 Belum Bayar)'),
        ('paid', 'Lunas / Dibayar'),
        ('done', 'Selesai Kontrak')
    ], string='Status Pembayaran', default='draft', readonly=True)

    wa_log_ids = fields.One2many('rental.wa.log', 'contract_id', string='Riwayat Pesan WA')

    # Validasi Mencegah Rumah Tersewa Ditempati Lagi
    @api.constrains('house_id', 'state')
    def _check_house_availability(self):
        for rec in self:
            if rec.house_id and rec.state in ['active', 'overdue']:
                existing_contract = self.search([
                    ('house_id', '=', rec.house_id.id),
                    ('id', '!=', rec.id),
                    ('state', 'in', ['active', 'overdue'])
                ], limit=1)
                if existing_contract:
                    raise ValidationError(
                        f"Unit Rumah '{rec.house_id.name}' TIDAK BISA DISEWA lagi karena saat ini sedang aktif ditempati oleh penyewa lain ({existing_contract.tenant_name})!"
                    )

    # Sequence Kode Kontrak Otomatis
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('rental.contract') or 'SEWA/001'
        return super(RentalContract, self).create(vals_list)

    def action_confirm(self):
        """ Mengubah status dari Draft ke Berjalan & Ubah Status Rumah ke Tersewa """
        for rec in self:
            if rec.house_id.status == 'rented':
                raise ValidationError(f"Rumah '{rec.house_id.name}' sudah berstatus Tersewa dan tidak dapat dipilih!")
            rec.state = 'active'
            rec.house_id.status = 'rented'

    def action_set_to_paid(self):
        """ Mengubah Status menjadi Lunas, Catat Ke Pembukuan, & Perpanjang Jatuh Tempo """
        for rec in self:
            # Otomatis catat transaksi ke menu Pembukuan Keuangan
            self.env['rental.accounting'].create({
                'contract_id': rec.id,
                'amount': rec.amount,
                'notes': f"Pembayaran sewa unit {rec.house_id.name} periode {rec.start_date} s/d {rec.due_date}"
            })
            
            # Perpanjang periode jatuh tempo
            if rec.payment_scheme == 'monthly':
                rec.due_date = fields.Date.add(rec.due_date, months=1)
            else:
                rec.due_date = fields.Date.add(rec.due_date, years=1)
            
            rec.state = 'active'

    # FUNGSI UNTUK SUTUS/SELESAI KONTRAK
    def action_terminate_contract(self):
        """ Mengakhiri Kontrak Sewa & Mengembalikan Status Rumah Menjadi Tersedia (Kosong) """
        for rec in self:
            rec.state = 'done'
            if rec.house_id:
                rec.house_id.status = 'available'

    def send_wa_message(self, phone, message):
        url = "https://api.fonnte.com/send"
        api_token = "MUHaJrm8k6LqYKLL6nkZ"
        payload = {'target': phone, 'message': message}
        headers = {'Authorization': api_token}
        status_log = 'failed'
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            _logger.info(f"Kirim WA ke {phone}: {response.text}")
            status_log = 'sent'
        except Exception as e:
            _logger.error(f"Gagal kirim WA ke {phone}: {str(e)}")

        self.env['rental.wa.log'].create({
            'contract_id': self.id,
            'phone': phone,
            'message': message,
            'status': status_log,
        })

    def action_manual_send_wa(self):
        for rec in self:
            msg = (
                f"Halo Sdr/i {rec.tenant_name},\n\n"
                f"Pemberitahuan tagihan sewa rumah *{rec.house_id.name}* "
                f"sebesar Rp {rec.amount:,.0f}.\n"
                f"Jatuh tempo: *{rec.due_date}*.\n"
                f"Status: *{dict(rec._fields['state'].selection).get(rec.state)}*."
            )
            rec.send_wa_message(rec.tenant_phone, msg)

    @api.model
    def _cron_check_rental_payments(self):
        today = fields.Date.today()
        contracts = self.search([('state', 'in', ['active', 'overdue'])])
        for contract in contracts:
            days_diff = (contract.due_date - today).days
            if days_diff == 5:
                msg = f"Pengingat tagihan sewa rumah *{contract.house_id.name}* sebesar Rp {contract.amount:,.0f} (H-5)."
                contract.send_wa_message(contract.tenant_phone, msg)
            elif days_diff == -1 and contract.state != 'overdue':
                contract.state = 'overdue'
                msg = f"⚠️ Tagihan sewa rumah *{contract.house_id.name}* telah JATUH TEMPO."
                contract.send_wa_message(contract.tenant_phone, msg)


class RentalAccounting(models.Model):
    _name = 'rental.accounting'
    _description = 'Pembukuan Keuangan Sewa'
    _order = 'payment_date desc, id desc'

    name = fields.Char(string='No. Transaksi', required=True, copy=False, readonly=True, default='New')
    contract_id = fields.Many2one('rental.contract', string='Kontrak Sewa', required=True, ondelete='cascade')
    tenant_name = fields.Char(related='contract_id.tenant_name', string='Nama Penyewa', store=True)
    house_id = fields.Many2one(related='contract_id.house_id', string='Unit Rumah', store=True)
    payment_date = fields.Date(string='Tanggal Bayar', default=fields.Date.today, required=True)
    amount = fields.Float(string='Nominal (Rp)', required=True)
    payment_method = fields.Selection([
        ('transfer', 'Transfer Bank'),
        ('cash', 'Tunai / Cash')
    ], string='Metode Pembayaran', default='transfer', required=True)
    notes = fields.Text(string='Catatan Pembukuan')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('rental.accounting') or 'ACC/001'
        return super(RentalAccounting, self).create(vals_list)


class RentalWALog(models.Model):
    _name = 'rental.wa.log'
    _description = 'Log Pengiriman WhatsApp'
    _order = 'send_date desc'

    contract_id = fields.Many2one('rental.contract', string='Kontrak Sewa', ondelete='cascade')
    phone = fields.Char(string='No. WhatsApp Target')
    message = fields.Text(string='Isi Pesan')
    send_date = fields.Datetime(string='Waktu Kirim', default=fields.Datetime.now)
    status = fields.Selection([
        ('sent', 'Terkirim'),
        ('failed', 'Gagal')
    ], string='Status Pengiriman', default='sent')