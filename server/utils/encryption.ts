import { execSync } from 'child_process'
import { join } from 'path'

/**
 * Decrypt configuration values by calling the Python backend's encryption utilities
 * This avoids reimplementing Fernet in Node.js and ensures we use the exact same decryption
 */
export class ConfigEncryption {
  private pythonScriptPath: string
  private initialized = false

  constructor() {
    // Path to the decrypt script relative to the project root
    // In Nuxt server context, we need to resolve from the project root
    const projectRoot = process.cwd()
    this.pythonScriptPath = join(projectRoot, 'scripts', 'decrypt_value.py')
  }

  /**
   * Initialize - check that Python script exists
   */
  private initialize(): void {
    if (this.initialized) {
      return
    }

    // Just mark as initialized - we'll check script exists when needed
    this.initialized = true
  }

  /**
   * Decrypt an encrypted value by calling the Python backend
   */
  decryptValue(encryptedValue: string): string | null {
    if (!encryptedValue) {
      return ''
    }

    this.initialize()

    try {
      // Try python3 first, fall back to python if python3 isn't available
      // Call the Python script to decrypt the value
      // Use stdin to avoid shell escaping issues with special characters
      let pythonCmd = 'python3'
      try {
        execSync('python3 --version', { stdio: 'ignore' })
      } catch {
        pythonCmd = 'python'
      }
      
      const result = execSync(`${pythonCmd} "${this.pythonScriptPath}"`, {
        input: encryptedValue,
        encoding: 'utf8',
        maxBuffer: 10 * 1024 * 1024, // 10MB buffer for large values
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env } // Pass environment variables (including SEERRBRIDGE_MASTER_KEY)
      })

      // Parse the JSON response
      const parsed = JSON.parse(result.trim())
      
      if (parsed.value !== undefined) {
        if (parsed.value === null) {
          // Value is plaintext (not encrypted)
          return null
        }
        
        // Successfully decrypted
        return parsed.value
      }
      
      // Unexpected response format
      return null
    } catch (error: any) {
      // If Python script fails (maybe not encrypted, or script error), treat as plaintext
      // Only log actual errors that indicate a configuration problem
      if (error.status !== undefined || error.code === 'ENOENT' || error.code === 127) {
        // Python not available - silently treat as plaintext
        return null
      }
      
      // For other errors, silently treat as plaintext
      return null
    }
  }

  /**
   * Check if a value appears to be encrypted
   * This calls the Python backend's is_encrypted method
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
export const configEncryption = new ConfigEncryption()

