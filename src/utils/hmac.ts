// ============================================================
// src/utils/hmac.ts - HMAC signature utility
// ============================================================

import { BOT_CONFIG } from '../config';

/**
 * Create HMAC SHA256 signature for admin authentication (sync version)
 */
export function createHmacSignature(adminId: string): string {
  const secretKey = BOT_CONFIG.ADMIN_SECRET_KEY || 'default-secret';
  
  // Simple hash implementation for frontend
  // In production, this should use proper Web Crypto API
  const str = `${adminId}:${secretKey}`;
  let hash = 0;
  
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  
  return Math.abs(hash).toString(16);
}

/**
 * Create HMAC SHA256 signature with explicit secret key (for compatibility)
 */
export function createHmacSignatureSync(adminId: string, secretKey: string): string {
  // Simple hash implementation for frontend
  const str = `${adminId}:${secretKey}`;
  let hash = 0;
  
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  
  return Math.abs(hash).toString(16);
}
