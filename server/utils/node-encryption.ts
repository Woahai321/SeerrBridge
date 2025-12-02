import { createHash, pbkdf2Sync } from 'node:crypto'
import Fernet from 'fernet'

/**
 * Node.js encryption utility that matches the Python encryption logic
 * Uses the same PBKDF2 key derivation and Fernet encryption as the Python backend
 */
export class NodeConfigEncryption {
  private fernet: Fernet | null = null
  private initialized = false

  /**
   * Initialize encryption with master key from environment
   * Matches the Python encryption_utils.py logic exactly
   */
  private initialize(): void {
    if (this.initialized) {
      return
    }

    try {
      // Get master key from environment - REQUIRED for production
      const masterKey = process.env.SEERRBRIDGE_MASTER_KEY
      if (!masterKey) {
        throw new Error('SEERRBRIDGE_MASTER_KEY environment variable is required')
      }

      // Derive salt from master key for consistency (same as Python)
      // This ensures deterministic encryption while keeping salt unique per master key
      const saltHash = createHash('sha256')
      saltHash.update(Buffer.from('SeerrBridge_Salt_Version_1.0'))
      saltHash.update(Buffer.from(masterKey))
      const salt = saltHash.digest().slice(0, 16) // Use first 16 bytes for salt (PBKDF2 requirement)

      // Derive encryption key using PBKDF2 (same as Python)
      const key = pbkdf2Sync(
        Buffer.from(masterKey),
        salt,
        100000, // 100k iterations (same as Python)
        32, // 32 bytes key length
        'sha256'
      )

      // Create Fernet instance with the derived key (base64url encoded, same as Python)
      const fernetKey = key.toString('base64url')
      this.fernet = new Fernet(fernetKey)
      this.initialized = true
    } catch (error) {
      console.error('Failed to initialize Node.js encryption:', error)
      throw error
    }
  }

  /**
   * Encrypt a sensitive value
   * Matches Python's encrypt_value method exactly
   */
  encryptValue(value: string): string {
    if (!value) {
      return ''
    }

    this.initialize()

    if (!this.fernet) {
      throw new Error('Encryption not initialized')
    }

    try {
      // Encrypt and return as base64url string (same as Python)
      const encrypted = this.fernet.encrypt(value)
      return encrypted
    } catch (error) {
      console.error('Failed to encrypt value:', error)
      throw error
    }
  }

  /**
   * Decrypt an encrypted value
   * Matches Python's decrypt_value method exactly
   */
  decryptValue(encryptedValue: string): string {
    if (!encryptedValue) {
      return ''
    }

    this.initialize()

    if (!this.fernet) {
      throw new Error('Encryption not initialized')
    }

    try {
      // Decrypt the base64url encoded value (same as Python)
      const decrypted = this.fernet.decrypt(encryptedValue)
      return decrypted
    } catch (error) {
      console.error('Failed to decrypt value:', error)
      throw error
    }
  }

  /**
   * Check if a value appears to be encrypted
   * Fernet tokens are base64url encoded and have a specific format
   */
  isEncrypted(value: string): boolean {
    if (!value || value.length < 44) {
      return false // Fernet tokens are at least 44 characters
    }

    try {
      // Try to decrypt it - if it succeeds, it's encrypted
      const decrypted = this.decryptValue(value)
      return decrypted !== null && decrypted !== value
    } catch {
      return false
    }
  }
}

// Global instance
export const nodeConfigEncryption = new NodeConfigEncryption()

