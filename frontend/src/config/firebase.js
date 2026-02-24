// Firebase Configuration
import { initializeApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  sendEmailVerification,
  createUserWithEmailAndPassword,
  deleteUser,
} from 'firebase/auth';

// Firebase configuration from environment variables
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || ""
};

// Initialize Firebase
let app = null;
let auth = null;
let googleProvider = null;

try {
  // Check if Firebase config is available
  if (firebaseConfig.apiKey && firebaseConfig.authDomain) {
    app = initializeApp(firebaseConfig);
    auth = getAuth(app);
    googleProvider = new GoogleAuthProvider();
    
    // Set additional scopes if needed
    googleProvider.addScope('email');
    googleProvider.addScope('profile');
    
    console.log("✅ Firebase initialized successfully");
  } else {
    console.warn("⚠️ Firebase configuration is incomplete. Firebase authentication will be disabled.");
  }
} catch (error) {
  console.error("❌ Firebase initialization error:", error);
}

export {
  app,
  auth,
  googleProvider,
  firebaseConfig,
  signInWithPopup,
  sendEmailVerification,
  createUserWithEmailAndPassword,
  deleteUser,
};
