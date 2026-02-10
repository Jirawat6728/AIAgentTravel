import React, { useEffect } from 'react';
import HomeHeader from '../../components/common/HomeHeader';
import './HomePage.css';

export default function HomePage({ onGetStarted, onSignIn, onSignOut, isLoggedIn, user, onNavigateToHome }) {
  useEffect(() => {
    document.body.classList.add('page-home');
    return () => document.body.classList.remove('page-home');
  }, []);

  return (
    <div className="home-container">
      {/* Header */}
      <HomeHeader 
        isLoggedIn={isLoggedIn}
        user={user}
        onSignIn={onSignIn}
        onSignOut={onSignOut}
        onGetStarted={onGetStarted}
        onNavigateToHome={onNavigateToHome}
      />

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-background">
          <div className="gradient-overlay"></div>
          <div className="animated-shapes">
            <div className="shape shape-1"></div>
            <div className="shape shape-2"></div>
            <div className="shape shape-3"></div>
          </div>
        </div>
        
        <div className="hero-content">
          <div className="hero-badge">
            <span className="badge-text">✨ ขับเคลื่อนด้วย AI</span>
          </div>
          <h1 className="hero-title">
            ผู้ช่วยวางแผนท่องเที่ยว AI ส่วนตัวของคุณ
          </h1>
          <p className="hero-subtitle">
            วางแผนทริปในฝันด้วย AI ค้นหาเที่ยวบิน โรงแรม และรับคำแนะนำส่วนตัวได้ทันที
          </p>
          
            
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features-section">
        <div className="features-content">
          <div className="section-header">
            <h2 className="section-title">ทำไมต้องเลือก AI Travel Agent?</h2>
            <p className="section-subtitle">สัมผัสการวางแผนท่องเที่ยวแห่งอนาคต</p>
          </div>

          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon feature-icon-blue">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="feature-title">ตอบสนองด้วย AI ทันที</h3>
              <p className="feature-description">รับคำตอบแบบเรียลไทม์สำหรับคำถามเกี่ยวกับการเดินทาง ด้วย Google Gemini AI</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-green">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
              </div>
              <h3 className="feature-title">ค้นหาเที่ยวบินทั่วโลก</h3>
              <p className="feature-description">เข้าถึงข้อมูลเที่ยวบินแบบเรียลไทม์จาก Amadeus API ครอบคลุมจุดหมายทั่วโลก</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-purple">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <h3 className="feature-title">จองที่พัก</h3>
              <p className="feature-description">ค้นหาและเปรียบเทียบโรงแรมด้วยราคาที่แข่งขันได้และข้อมูลรายละเอียด</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-orange">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h3 className="feature-title">สนทนาธรรมชาติ</h3>
              <p className="feature-description">แชทเป็นภาษาไทยหรืออังกฤษได้ตามธรรมชาติ AI เข้าใจความต้องการการเดินทางของคุณ</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-pink">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="feature-title">พร้อมบริการ 24/7</h3>
              <p className="feature-description">วางแผนทริปได้ทุกที่ทุกเวลา ด้วยผู้ช่วย AI ที่พร้อมให้บริการตลอด</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-teal">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="feature-title">ผลลัพธ์ที่เชื่อถือได้</h3>
              <p className="feature-description">ข้อมูลเที่ยวบินและโรงแรมทั้งหมดมาจาก Amadeus travel API ที่น่าเชื่อถือ</p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="how-it-works-section">
        <div className="how-it-works-content">
          <div className="section-header">
            <h2 className="section-title">ใช้งานอย่างไร</h2>
            <p className="section-subtitle">เริ่มวางแผนทริปในฝันได้ใน 3 ขั้นตอนง่ายๆ</p>
          </div>

          <div className="steps-container">
            <div className="step-card">
              <div className="step-number">1</div>
              <div className="step-content">
                <h3 className="step-title">ถามคำถามของคุณ</h3>
                <p className="step-description">พิมพ์ว่าอยากไปที่ไหนหรือกำลังหาอะไร AI ของเรารู้จักภาษาธรรมชาติ</p>
              </div>
            </div>

            <div className="step-arrow">→</div>

            <div className="step-card">
              <div className="step-number">2</div>
              <div className="step-content">
                <h3 className="step-title">AI ค้นหาให้คุณ</h3>
                <p className="step-description">AI วิเคราะห์คำขอและค้นหาจากเที่ยวบินและโรงแรมหลายพันรายการให้คุณ</p>
              </div>
            </div>

            <div className="step-arrow">→</div>

            <div className="step-card">
              <div className="step-number">3</div>
              <div className="step-content">
                <h3 className="step-title">รับผลลัพธ์ทันที</h3>
                <p className="step-description">รับคำแนะนำส่วนตัวพร้อมราคา เวลา และรายละเอียดที่คุณต้องการ</p>
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2 className="cta-title">พร้อมเริ่มเดินทางแล้วหรือยัง?</h2>
          <p className="cta-subtitle">ร่วมกับนักเดินทางหลายพันคนที่เชื่อใจ AI Travel Agent</p>
          <button onClick={onGetStarted} className="cta-button">
            เริ่มต้นเลย
            <svg className="arrow-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-section">
            <div className="footer-logo">
              <div className="footer-logo-brand">
                <svg className="footer-logo-plane" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
                </svg>
                <span className="footer-logo-text">AI Travel Agent</span>
              </div>
            </div>
            <p className="footer-description">ผู้ช่วยอัจฉริยะสำหรับการวางแผนเดินทางอย่างราบรื่น</p>
          </div>

          <div className="footer-section">
            <h4 className="footer-title">ผลิตภัณฑ์</h4>
            <a href="#features" className="footer-link">ฟีเจอร์</a>
            <a href="#how-it-works" className="footer-link">วิธีใช้งาน</a>
            <a href="#destinations" className="footer-link">จุดหมาย</a>
          </div>

          <div className="footer-section">
            <h4 className="footer-title">บริษัท</h4>
            <a href="#about" className="footer-link">เกี่ยวกับเรา</a>
            <a href="#" className="footer-link">ติดต่อ</a>
            <a href="#" className="footer-link">นโยบายความเป็นส่วนตัว</a>
          </div>

          <div className="footer-section">
            <h4 className="footer-title">ติดตามเรา</h4>
            <a href="#" className="footer-link">Twitter</a>
            <a href="#" className="footer-link">Facebook</a>
            <a href="#" className="footer-link">Instagram</a>
          </div>
        </div>

        <div className="footer-bottom">
          <p>© 2025 AI Travel Agent ขับเคลื่อนโดย Gemini และ Amadeus</p>
        </div>
      </footer>
    </div>
  );
}