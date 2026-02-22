import { Body, Controller, Post } from '@nestjs/common';
import { MailService, SendDto } from './mail.service';

@Controller()
export class MailController {
  constructor(private readonly mailService: MailService) {}

  @Post('send')
  async send(@Body() dto: SendDto) {
    return this.mailService.send(dto);
  }
}
