// ============================================================
// src/utils/adminAuth.ts — Helper для HMAC аутентификации
// ============================================================

/**
 * Генерирует HMAC SHA256 подпись для аутентификации админа
 * @param adminId - ID администратора
 * @param secretKey - Секретный ключ
 * @returns HMAC подпись в hex формате
 */
export async function generateAdminSignature(adminId: number, secretKey: string): Promise<string> {
  const message = adminId.toString();
  const encoder = new TextEncoder();
  const keyData = encoder.encode(secretKey);
  const messageData = encoder.encode(message);

  const key = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', key, messageData);
  
  // Конвертируем ArrayBuffer в hex string
  const hexArray = Array.from(new Uint8Array(signature));
  const hexString = hexArray.map(b => b.toString(16).padStart(2, '0')).join('');
  
  return hexString;
}

/**
 * Создает headers для admin API запросов
 * @param adminId - ID администратора
 * @param secretKey - Секретный ключ
 * @returns Headers объект с x-admin-id и x-admin-signature
 */
export async function createAdminHeaders(adminId: number, secretKey: string): Promise<HeadersInit> {
  const signature = await generateAdminSignature(adminId, secretKey);
  
  return {
    'x-admin-id': adminId.toString(),
    'x-admin-signature': signature,
    'Content-Type': 'application/json',
  };
}
