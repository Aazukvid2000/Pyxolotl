"""
Utilidades para envío de emails
Usa SendGrid para emails transaccionales
"""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EmailService:
    """Servicio para envío de correos electrónicos"""
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.SENDGRID_FROM_EMAIL
        self.from_name = settings.SENDGRID_FROM_NAME
        
        if self.api_key:
            self.client = SendGridAPIClient(self.api_key)
        else:
            self.client = None
            logger.warning("SendGrid API key no configurada - modo simulación")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Envía un email
        
        Args:
            to_email: Email del destinatario
            subject: Asunto del email
            html_content: Contenido HTML
            plain_content: Contenido en texto plano (opcional)
        
        Returns:
            True si se envió exitosamente
        """
        logger.info(f"[EMAIL] Intentando enviar email a {to_email}")
        logger.info(f"[EMAIL] API Key configurada: {bool(self.api_key)}")
        logger.info(f"[EMAIL] From: {self.from_email}")
        
        if not self.client:
            # Modo simulación
            logger.warning(f"[SIMULACIÓN] Email a {to_email}: {subject}")
            logger.debug(f"Contenido: {html_content[:100]}...")
            return True
        
        try:
            logger.info(f"[EMAIL] Creando mensaje de SendGrid...")
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            if plain_content:
                message.add_content(Content("text/plain", plain_content))
            
            logger.info(f"[EMAIL] Enviando a través de SendGrid...")
            response = self.client.send(message)
            
            logger.info(f"[EMAIL] Respuesta de SendGrid: {response.status_code}")
            logger.info(f"[EMAIL] Headers: {response.headers}")
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ [EMAIL] Email enviado exitosamente a {to_email}")
                return True
            else:
                logger.error(f"❌ [EMAIL] Error al enviar email: {response.status_code}")
                logger.error(f"[EMAIL] Body: {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [EMAIL] Excepción al enviar email: {str(e)}")
            import traceback
            logger.error(f"[EMAIL] Traceback: {traceback.format_exc()}")
            return False
    
    def send_verification_email(self, to_email: str, nombre: str, token: str) -> bool:
        """Envía email de verificación de cuenta"""
        
        verify_url = f"{settings.FRONTEND_URL}/verificar?token={token}"
        
        subject = settings.EMAIL_VERIFICATION_SUBJECT
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(90deg, #4ea3ff, #7b61ff); padding: 20px; text-align: center; color: white; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: linear-gradient(90deg, #4ea3ff, #7b61ff); color: white; text-decoration: none; border-radius: 8px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎮 Bienvenido a Pyxolotl</h1>
                </div>
                <div class="content">
                    <h2>¡Hola {nombre}!</h2>
                    <p>Gracias por registrarte en Pyxolotl, la plataforma para desarrolladores indie mexicanos.</p>
                    <p>Para activar tu cuenta, por favor verifica tu correo electrónico haciendo clic en el siguiente botón:</p>
                    <div style="text-align: center;">
                        <a href="{verify_url}" class="button">Verificar mi cuenta</a>
                    </div>
                    <p>O copia y pega este enlace en tu navegador:</p>
                    <p style="background: #fff; padding: 10px; border-radius: 5px; word-break: break-all;">
                        {verify_url}
                    </p>
                    <p>Este enlace expirará en 24 horas.</p>
                    <p>Si no creaste esta cuenta, puedes ignorar este mensaje.</p>
                </div>
                <div class="footer">
                    <p>© 2025 Pyxolotl - Plataforma de Videojuegos Indie</p>
                    <p>Este es un correo automático, por favor no respondas.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_purchase_confirmation(
        self,
        to_email: str,
        nombre: str,
        numero_orden: str,
        juegos: list,
        total: float
    ) -> bool:
        """Envía confirmación de compra con enlaces de descarga"""
        
        subject = settings.EMAIL_PURCHASE_SUBJECT
        
        # Generar lista de juegos
        juegos_html = ""
        for juego in juegos:
            download_url = f"{settings.FRONTEND_URL}/biblioteca"
            juegos_html += f"""
            <div style="background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #7b61ff;">
                <h3 style="margin: 0 0 10px 0;">🎮 {juego['titulo']}</h3>
                <p style="margin: 5px 0;">Precio: ${juego['precio']:.2f} USD</p>
                <a href="{download_url}" style="color: #7b61ff; text-decoration: none;">📥 Ir a mi biblioteca →</a>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(90deg, #4ea3ff, #7b61ff); padding: 20px; text-align: center; color: white; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: linear-gradient(90deg, #4ea3ff, #7b61ff); color: white; text-decoration: none; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ ¡Compra Confirmada!</h1>
                </div>
                <div class="content">
                    <h2>¡Gracias por tu compra, {nombre}!</h2>
                    <p><strong>Número de orden:</strong> {numero_orden}</p>
                    <p><strong>Total pagado:</strong> ${total:.2f} USD</p>
                    
                    <h3>Tus juegos:</h3>
                    {juegos_html}
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{settings.FRONTEND_URL}/biblioteca" class="button">Ir a mi biblioteca</a>
                    </div>
                    
                    <p style="margin-top: 20px;">Puedes descargar tus juegos en cualquier momento desde tu biblioteca.</p>
                </div>
                <div style="text-align: center; color: #666; font-size: 12px; margin-top: 20px;">
                    <p>© 2025 Pyxolotl - Plataforma de Videojuegos Indie</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_game_approved(self, to_email: str, nombre: str, titulo_juego: str) -> bool:
        """Notifica que un juego fue aprobado"""
        
        subject = settings.EMAIL_GAME_APPROVED_SUBJECT
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 30px; border-radius: 10px;">
                <h1 style="color: #4CAF50;">🎉 ¡Tu juego ha sido aprobado!</h1>
                <p>Hola {nombre},</p>
                <p>Tenemos excelentes noticias: tu juego <strong>"{titulo_juego}"</strong> ha sido revisado y aprobado.</p>
                <p>Ya está visible en el catálogo público de Pyxolotl y los usuarios pueden comprarlo.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.FRONTEND_URL}/" style="display: inline-block; padding: 12px 24px; background: #4CAF50; color: white; text-decoration: none; border-radius: 8px;">Ver en catálogo</a>
                </div>
                <p>¡Mucha suerte con las ventas!</p>
                <p style="color: #666; font-size: 12px; margin-top: 30px;">- El equipo de Pyxolotl</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_game_rejected(
        self,
        to_email: str,
        nombre: str,
        titulo_juego: str,
        motivo: str
    ) -> bool:
        """Notifica que un juego fue rechazado"""
        
        subject = settings.EMAIL_GAME_REJECTED_SUBJECT
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 30px; border-radius: 10px;">
                <h1 style="color: #ff6b6b;">Tu juego necesita cambios</h1>
                <p>Hola {nombre},</p>
                <p>Hemos revisado tu juego <strong>"{titulo_juego}"</strong> y necesita algunos ajustes antes de ser publicado:</p>
                <div style="background: white; padding: 15px; margin: 20px 0; border-left: 4px solid #ff6b6b; border-radius: 5px;">
                    <p><strong>Motivo:</strong></p>
                    <p>{motivo}</p>
                </div>
                <p>Por favor realiza los cambios necesarios y vuelve a enviar tu juego para revisión.</p>
                <p>Si tienes dudas, no dudes en contactarnos.</p>
                <p style="color: #666; font-size: 12px; margin-top: 30px;">- El equipo de Pyxolotl</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)

# Instancia global del servicio
email_service = EmailService()