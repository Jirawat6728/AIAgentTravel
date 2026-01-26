/**
 * Text Correction and Language Detection Utilities
 * สำหรับแก้ไข typo และตรวจสอบภาษา
 */

// Common Thai typos and corrections
const THAI_TYPO_MAP = {
  // Common keyboard layout mistakes (Thai -> English)
  'อยาก': 'อยาก',
  'เที่ยว': 'เที่ยว',
  'พัก': 'พัก',
  'โรงแรม': 'โรงแรม',
  'เที่ยวบิน': 'เที่ยวบิน',
  'ราคา': 'ราคา',
  'วันที่': 'วันที่',
  'เวลา': 'เวลา',
  'คน': 'คน',
  'วัน': 'วัน',
  'คืน': 'คืน',
  'ไป': 'ไป',
  'กลับ': 'กลับ',
  'จาก': 'จาก',
  'ถึง': 'ถึง',
  // Common English typos when typing in Thai mode
  ';': ';',
  '[': '[',
  ']': ']',
  "'": "'",
  '"': '"',
  ',': ',',
  '.': '.',
  '/': '/',
  '-': '-',
  '=': '=',
};

// Common English typos
const ENGLISH_TYPO_MAP = {
  'hotel': 'hotel',
  'flight': 'flight',
  'travel': 'travel',
  'trip': 'trip',
  'booking': 'booking',
  'price': 'price',
  'date': 'date',
  'time': 'time',
  'people': 'people',
  'days': 'days',
  'nights': 'nights',
  'from': 'from',
  'to': 'to',
};

/**
 * Detect if text is primarily Thai or English
 */
export function detectLanguage(text) {
  if (!text || text.trim().length === 0) {
    return 'unknown';
  }

  const thaiCharCount = (text.match(/[\u0E00-\u0E7F]/g) || []).length;
  const englishCharCount = (text.match(/[a-zA-Z]/g) || []).length;
  const totalChars = text.replace(/\s/g, '').length;

  if (totalChars === 0) {
    return 'unknown';
  }

  const thaiRatio = thaiCharCount / totalChars;
  const englishRatio = englishCharCount / totalChars;

  if (thaiRatio > 0.3) {
    return 'thai';
  } else if (englishRatio > 0.5) {
    return 'english';
  } else if (thaiCharCount > englishCharCount) {
    return 'thai';
  } else if (englishCharCount > thaiCharCount) {
    return 'english';
  }

  return 'mixed';
}

/**
 * Calculate Levenshtein distance between two strings
 */
function levenshteinDistance(str1, str2) {
  const m = str1.length;
  const n = str2.length;
  const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

  for (let i = 0; i <= m; i++) {
    dp[i][0] = i;
  }
  for (let j = 0; j <= n; j++) {
    dp[0][j] = j;
  }

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (str1[i - 1] === str2[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1];
      } else {
        dp[i][j] = Math.min(
          dp[i - 1][j] + 1,     // deletion
          dp[i][j - 1] + 1,     // insertion
          dp[i - 1][j - 1] + 1  // substitution
        );
      }
    }
  }

  return dp[m][n];
}

/**
 * Find closest match from a dictionary
 */
function findClosestMatch(word, dictionary, maxDistance = 2) {
  let bestMatch = null;
  let minDistance = Infinity;

  for (const dictWord of dictionary) {
    const distance = levenshteinDistance(word.toLowerCase(), dictWord.toLowerCase());
    if (distance < minDistance && distance <= maxDistance) {
      minDistance = distance;
      bestMatch = dictWord;
    }
  }

  return minDistance <= maxDistance ? bestMatch : null;
}

/**
 * Common Thai travel-related words
 */
const THAI_TRAVEL_WORDS = [
  'เที่ยว', 'ทริป', 'พัก', 'โรงแรม', 'เที่ยวบิน', 'ราคา', 'วันที่', 'เวลา',
  'คน', 'วัน', 'คืน', 'ไป', 'กลับ', 'จาก', 'ถึง', 'จอง', 'จองโรงแรม',
  'จองเที่ยวบิน', 'ที่พัก', 'รีสอร์ท', 'บิน', 'สนามบิน', 'ตั๋ว', 'แพ็คเกจ',
  'ทัวร์', 'เที่ยว', 'พักผ่อน', 'ทะเล', 'ภูเขา', 'ต่างประเทศ', 'ในประเทศ',
  'กรุงเทพ', 'เชียงใหม่', 'ภูเก็ต', 'พัทยา', 'เกาะ', 'หาด', 'น้ำตก'
];

/**
 * Common English travel-related words
 */
const ENGLISH_TRAVEL_WORDS = [
  'hotel', 'flight', 'travel', 'trip', 'booking', 'price', 'date', 'time',
  'people', 'days', 'nights', 'from', 'to', 'book', 'reserve', 'accommodation',
  'resort', 'airport', 'ticket', 'package', 'tour', 'vacation', 'beach',
  'mountain', 'international', 'domestic', 'bangkok', 'chiangmai', 'phuket',
  'pattaya', 'island', 'waterfall', 'want', 'need', 'help', 'find', 'recommend',
  'see', 'choose', 'buy', 'airline', 'airplane', 'plane', 'checkin', 'checkout',
  'room', 'swimming', 'pool', 'breakfast', 'lunch', 'dinner', 'buffet', 'wifi',
  'internet', 'car', 'rental', 'taxi', 'bus', 'train', 'boat', 'ferry',
  'adult', 'child', 'baby', 'bed', 'single', 'double', 'twin', 'morning',
  'afternoon', 'evening', 'night', 'midnight', 'cheap', 'expensive', 'discount',
  'promotion', 'coupon', 'confirm', 'cancel', 'change', 'edit', 'thailand',
  'japan', 'korea', 'china', 'singapore', 'malaysia', 'vietnam', 'cambodia',
  'laos', 'myanmar', 'india', 'nepal', 'england', 'france', 'italy', 'spain',
  'germany', 'switzerland', 'australia', 'newzealand', 'america', 'canada', 'mexico'
];

/**
 * Correct typos in text
 */
export function correctTypos(text) {
  if (!text || text.trim().length === 0) {
    return { corrected: text, suggestions: [] };
  }

  const language = detectLanguage(text);
  const words = text.split(/\s+/);
  const corrections = [];
  const suggestions = [];

  const correctedWords = words.map((word, index) => {
    // Skip if word is too short or contains numbers/special chars only
    if (word.length < 2 || /^[0-9\s\-.,!?]+$/.test(word)) {
      return word;
    }

    let corrected = word;
    let suggestion = null;

    if (language === 'thai' || language === 'mixed') {
      // Check against Thai travel words
      const thaiMatch = findClosestMatch(word, THAI_TRAVEL_WORDS, 2);
      if (thaiMatch && thaiMatch !== word) {
        corrected = thaiMatch;
        suggestion = thaiMatch;
        corrections.push({ original: word, corrected: thaiMatch, index });
      }
    }

    if (language === 'english' || language === 'mixed') {
      // Check against English travel words
      const englishMatch = findClosestMatch(word, ENGLISH_TRAVEL_WORDS, 2);
      if (englishMatch && englishMatch !== word) {
        corrected = englishMatch;
        suggestion = englishMatch;
        corrections.push({ original: word, corrected: englishMatch, index });
      }
    }

    return corrected;
  });

  const correctedText = correctedWords.join(' ');

  return {
    corrected: correctedText,
    original: text,
    corrections: corrections,
    language: language,
    hasCorrections: corrections.length > 0
  };
}

/**
 * Suggest corrections with confidence score
 */
export function suggestCorrections(text, minConfidence = 0.7) {
  const result = correctTypos(text);
  
  if (!result.hasCorrections) {
    return null;
  }

  const suggestions = result.corrections.map(corr => ({
    original: corr.original,
    suggested: corr.corrected,
    confidence: 0.8, // Simplified confidence score
    position: corr.index
  }));

  return {
    original: text,
    corrected: result.corrected,
    suggestions: suggestions,
    language: result.language
  };
}

/**
 * Auto-detect and suggest language switch
 */
export function detectLanguageMismatch(text, expectedLanguage = null) {
  const detected = detectLanguage(text);
  
  // If user is typing in wrong language (e.g., typing English when expecting Thai)
  if (expectedLanguage && detected !== expectedLanguage && detected !== 'mixed') {
    return {
      detected: detected,
      expected: expectedLanguage,
      mismatch: true,
      suggestion: `คุณกำลังพิมพ์เป็น${detected === 'english' ? 'ภาษาอังกฤษ' : 'ภาษาไทย'} แต่ระบบคาดหวัง${expectedLanguage === 'english' ? 'ภาษาอังกฤษ' : 'ภาษาไทย'}`
    };
  }

  return {
    detected: detected,
    expected: expectedLanguage,
    mismatch: false
  };
}
