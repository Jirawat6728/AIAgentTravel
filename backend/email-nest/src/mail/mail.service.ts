import { Injectable } from '@nestjs/common';
import { MailerService } from '@nestjs-modules/mailer';

export interface SendDto {
  to: string;
  subject: string;
  html?: string;
  template?: string;
  context?: Record<string, unknown>;
}

@Injectable()
export class MailService {
  constructor(private readonly mailerService: MailerService) {}

  async send(dto: SendDto): Promise<{ ok: boolean; message?: string }> {
    const { to, subject, html, template, context } = dto;

    if (!to || !subject) {
      return { ok: false, message: 'to and subject are required' };
    }

    try {
      if (template && context) {
        await this.mailerService.sendMail({
          to,
          subject,
          template,
          context,
        });
      } else if (html) {
        await this.mailerService.sendMail({
          to,
          subject,
          template: 'wrap-html',
          context: { body: html },
        });
      } else {
        return { ok: false, message: 'Provide either html or template+context' };
      }
      return { ok: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { ok: false, message };
    }
  }
}
