import React, { useEffect } from 'react';
import HomeHeader from '../../components/common/HomeHeader';
import './HomePage.css';
import { useLanguage } from '../../context/LanguageContext';

export default function HomePage({ onGetStarted, onSignIn, onSignOut, isLoggedIn, user, onNavigateToHome }) {
  const { t } = useLanguage();
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
            <span className="badge-text">{t('home.badge')}</span>
          </div>
          <h1 className="hero-title">
            {t('home.heroTitle')}
          </h1>
          <p className="hero-subtitle">
            {t('home.heroDesc')}
          </p>
          
            
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features-section">
        <div className="features-content">
          <div className="section-header">
            <h2 className="section-title">{t('home.whyChoose')}</h2>
            <p className="section-subtitle">{t('home.experienceFuture')}</p>
          </div>

          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon feature-icon-blue">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="feature-title">{t('home.feature1Title')}</h3>
              <p className="feature-description">{t('home.feature1Desc')}</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-green">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
              </div>
              <h3 className="feature-title">{t('home.feature2Title')}</h3>
              <p className="feature-description">{t('home.feature2Desc')}</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-purple">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <h3 className="feature-title">{t('home.feature3Title')}</h3>
              <p className="feature-description">{t('home.feature3Desc')}</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-orange">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h3 className="feature-title">{t('home.feature4Title')}</h3>
              <p className="feature-description">{t('home.feature4Desc')}</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-pink">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="feature-title">{t('home.feature5Title')}</h3>
              <p className="feature-description">{t('home.feature5Desc')}</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-teal">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="feature-title">{t('home.feature6Title')}</h3>
              <p className="feature-description">{t('home.feature6Desc')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="how-it-works-section">
        <div className="how-it-works-content">
          <div className="section-header">
            <h2 className="section-title">{t('home.howItWorks')}</h2>
            <p className="section-subtitle">{t('home.howItWorksDesc')}</p>
          </div>

          <div className="steps-container">
            <div className="step-card">
              <div className="step-number">1</div>
              <div className="step-content">
                <h3 className="step-title">{t('home.step1Title')}</h3>
                <p className="step-description">{t('home.step1Desc')}</p>
              </div>
            </div>

            <div className="step-arrow">→</div>

            <div className="step-card">
              <div className="step-number">2</div>
              <div className="step-content">
                <h3 className="step-title">{t('home.step2Title')}</h3>
                <p className="step-description">{t('home.step2Desc')}</p>
              </div>
            </div>

            <div className="step-arrow">→</div>

            <div className="step-card">
              <div className="step-number">3</div>
              <div className="step-content">
                <h3 className="step-title">{t('home.step3Title')}</h3>
                <p className="step-description">{t('home.step3Desc')}</p>
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2 className="cta-title">{t('home.ctaTitle')}</h2>
          <p className="cta-subtitle">{t('home.ctaDesc')}</p>
          <button onClick={onGetStarted} className="cta-button">
            {t('home.getStarted')}
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
              <div className="footer-logo-icon">
                <svg className="footer-logo-plane" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
                </svg>
              </div>
              <span className="footer-logo-text">AI Travel Agent</span>
            </div>
            <p className="footer-description">{t('home.footerDesc')}</p>
          </div>

          <div className="footer-section">
            <h4 className="footer-title">{t('home.footerProduct')}</h4>
            <a href="#features" className="footer-link">{t('home.footerFeatures')}</a>
            <a href="#how-it-works" className="footer-link">{t('home.footerHowTo')}</a>
            <a href="#destinations" className="footer-link">{t('home.footerDestinations')}</a>
          </div>

          <div className="footer-section">
            <h4 className="footer-title">{t('home.footerCompany')}</h4>
            <a href="#about" className="footer-link">{t('home.footerAbout')}</a>
            <a href="#" className="footer-link">{t('home.footerContact')}</a>
            <a href="#" className="footer-link">{t('home.footerPrivacy')}</a>
          </div>

          <div className="footer-section">
            <h4 className="footer-title">{t('home.footerFollow')}</h4>
            <a href="#" className="footer-link">Twitter</a>
            <a href="#" className="footer-link">Facebook</a>
            <a href="#" className="footer-link">Instagram</a>
          </div>
        </div>

        <div className="footer-bottom">
          <p>{t('home.footerCopy')}</p>
        </div>
      </footer>
    </div>
  );
}