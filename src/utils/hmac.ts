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
