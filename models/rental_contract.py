import logging
import requests
from odoo import models, fields, api

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
    
    # Skema Cicilan
    payment_scheme = fields.Selection([
        ('monthly', 'Perbulan'),
        ('yearly', 'Pertahun')
    ], string='Skema Cicilan', default='monthly', required=True)
    
    start_date = fields.Date(string='Tanggal Masuk', default=fields.Date.today, required=True)
    due_date = fields.Date(string='Tanggal Jatuh Tempo', required=True)
    amount = fields.Float(string='Nominal Cicilan/Sewa', required=True)
    
    # Status Pembayaran
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Berjalan'),
        ('overdue', 'Jatuh Tempo (H+1 Belum Bayar)'),
        ('paid', 'Lunas / Dibayar')
    ], string='Status Pembayaran', default='draft', readonly=True)

    wa_log_ids = fields.One2many('rental.wa.log', 'contract_id', string='Riwayat Pesan WA')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('rental.contract') or 'New'
        records = super(RentalContract, self).create(vals_list)
        for rec in records:
            if rec.house_id:
                rec.house_id.status = 'rented'
        return records

    def action_confirm(self):
        """ Mengubah status dari Draft ke Berjalan """
        for rec in self:
            rec.state = 'active'

    def send_wa_message(self, phone, message):
        """ Fungsi Pengiriman Pesan via WhatsApp Gateway (Fonnte API) """
        url = "https://api.fonnte.com/send"
        api_token = "MUHaJrm8k6LqYKLL6nkZ"  # Token API Fonnte Terbaru
        
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
        """ Tombol Kirim WA Manual """
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
        """ Cron Job Harian Pengingat WA """
        today = fields.Date.today()
        contracts = self.search([('state', 'in', ['active', 'overdue'])])
        
        for contract in contracts:
            days_diff = (contract.due_date - today).days
            
            # H-5 Pengingat Cicilan
            if days_diff == 5:
                msg = (
                    f"Halo Sdr/i {contract.tenant_name},\n\n"
                    f"Pengingat tagihan sewa rumah *{contract.house_id.name}* "
                    f"sebesar Rp {contract.amount:,.0f}.\n"
                    f"Jatuh tempo pada tanggal: *{contract.due_date}* (H-5).\n"
                    f"Mohon melakukan pembayaran sebelum tanggal tersebut. Terima kasih!"
                )
                contract.send_wa_message(contract.tenant_phone, msg)
                
            # H+1 Belum Bayar -> Ubah Status ke Overdue
            elif days_diff == -1 and contract.state != 'overdue':
                contract.state = 'overdue'
                msg = (
                    f"⚠️ PEMBERITAHUAN JATUH TEMPO!\n\n"
                    f"Halo Sdr/i {contract.tenant_name},\n"
                    f"Tagihan sewa rumah *{contract.house_id.name}* telah JATUH TEMPO per tanggal {contract.due_date}.\n"
                    f"Status tagihan saat ini: *JATUH TEMPO (H+1 Belum Bayar)*.\n"
                    f"Mohon segera melakukan pembayaran. Terima kasih."
                )
                contract.send_wa_message(contract.tenant_phone, msg)
                
            # Mengirim WA Setiap Hari selama masih Overdue
            elif days_diff < -1 and contract.state == 'overdue':
                msg = (
                    f"🔴 PERINGATAN PEMBAYARAN JATUH TEMPO\n\n"
                    f"Halo Sdr/i {contract.tenant_name},\n"
                    f"Tagihan sewa rumah Anda sebesar Rp {contract.amount:,.0f} telah melewati jatuh tempo.\n"
                    f"Mohon SEGERA melakukan pembayaran."
                )
                contract.send_wa_message(contract.tenant_phone, msg)

    def action_set_to_paid(self):
        """ Mengubah Status menjadi Lunas / Dibayar """
        for rec in self:
            rec.state = 'paid'
            if rec.payment_scheme == 'monthly':
                rec.due_date = fields.Date.add(rec.due_date, months=1)
            else:
                rec.due_date = fields.Date.add(rec.due_date, years=1)
            rec.state = 'active'


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