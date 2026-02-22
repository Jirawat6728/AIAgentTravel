import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { join } from 'path';
import { config } from 'dotenv';

// Load backend/.env for SMTP_* and FROM_EMAIL
config({ path: join(__dirname, '..', '..', '.env') });

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors();
  const port = process.env.EMAIL_SERVICE_PORT || process.env.PORT || 3001;
  await app.listen(port);
  console.log(`Email service (NestJS Mailer) running on http://localhost:${port}`);
}
bootstrap();
