import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join } from 'path'

/**
 * Utility to read and write .env files
 */
export class EnvFileManager {
  private envPath: string

  constructor() {
    // Get .env file path from data directory (shared between containers)
    const projectRoot = process.cwd()
    // Use /app/data/.env in containers, or ./.env in local development
    const dataDir = process.env.NODE_ENV === 'production' 
      ? join(projectRoot, 'data')
      : projectRoot
    this.envPath = join(dataDir, '.env')
  }

  /**
   * Read all environment variables from .env file
   */
  readEnv(): Record<string, string> {
    const env: Record<string, string> = {}
    
    if (!existsSync(this.envPath)) {
      return env
    }

    try {
      const content = readFileSync(this.envPath, 'utf-8')
      const lines = content.split('\n')

      for (const line of lines) {
        const trimmed = line.trim()
        
        // Skip empty lines and comments
        if (!trimmed || trimmed.startsWith('#')) {
          continue
        }

        // Parse KEY=VALUE format
        const equalIndex = trimmed.indexOf('=')
        if (equalIndex === -1) {
          continue
        }

        const key = trimmed.substring(0, equalIndex).trim()
        let value = trimmed.substring(equalIndex + 1).trim()

        // Handle empty quoted strings (KEY="")
        if (value === '""' || value === "''") {
          env[key] = ''
        } else if ((value.startsWith('"') && value.endsWith('"')) || 
                   (value.startsWith("'") && value.endsWith("'"))) {
          // Remove quotes and unescape
          value = value.slice(1, -1)
          // Unescape in correct order: first handle \\, then \"
          // This prevents double-unescaping
          value = value.replace(/\\\\/g, '\u0000TEMP_BACKSLASH\u0000')  // Temporarily replace \\ with placeholder
                      .replace(/\\"/g, '"')                              // Unescape quotes
                      .replace(/\u0000TEMP_BACKSLASH\u0000/g, '\\')     // Restore backslashes
          env[key] = value
        } else {
          // Unquoted value (including empty string without quotes)
          env[key] = value
        }
      }
    } catch (error) {
      console.error('Error reading .env file:', error)
    }

    return env
  }

  /**
   * Write environment variables to .env file
   */
  writeEnv(env: Record<string, string | number | boolean | null | undefined>): void {
    const lines: string[] = []
    
    // Add header comment
    lines.push('# SeerrBridge Configuration')
    lines.push('# This file is auto-generated. Do not edit manually unless you know what you are doing.')
    lines.push('')

    // Sort keys for better readability
    const sortedKeys = Object.keys(env).sort()

    for (const key of sortedKeys) {
      const value = env[key]
      
      // Skip null/undefined values (but allow empty strings)
      if (value === null || value === undefined) {
        continue
      }

      // Convert value to string (empty strings are valid and should be written)
      let valueStr = String(value)
      
      // Check if value is a valid JSON object string (starts with { and ends with })
      const isJsonObject = valueStr.trim().startsWith('{') && valueStr.trim().endsWith('}')
      
      // Check if it's already a valid JSON string (can be parsed)
      let isValidJson = false
      if (isJsonObject) {
        try {
          JSON.parse(valueStr)
          isValidJson = true
        } catch {
          // Not valid JSON, treat as regular string
        }
      }
      
      // Handle different value types
      if (valueStr === '') {
        // Empty string should be written as KEY=""
        valueStr = '""'
      } else if (isValidJson) {
        // For valid JSON strings, ensure it's on a single line and escape for .env format
        // Remove any existing line breaks in the JSON string
        valueStr = valueStr.replace(/\n/g, '').replace(/\r/g, '')
        // Escape backslashes and quotes for .env file format
        valueStr = valueStr
          .replace(/\\/g, '\\\\')  // Escape backslashes first (if any)
          .replace(/"/g, '\\"')    // Escape quotes
        valueStr = `"${valueStr}"`  // Wrap in quotes for .env file
      } else if (isJsonObject || valueStr.includes(' ') || valueStr.includes('=') || valueStr.includes('#')) {
        // For non-JSON strings with special characters, escape quotes and backslashes
        valueStr = valueStr
          .replace(/\\/g, '\\\\')  // Escape backslashes first
          .replace(/"/g, '\\"')    // Then escape quotes
        valueStr = `"${valueStr}"`
      }
      // If value doesn't need quotes, write it exactly as-is (no escaping)

      lines.push(`${key}=${valueStr}`)
    }

    try {
      writeFileSync(this.envPath, lines.join('\n') + '\n', 'utf-8')
    } catch (error) {
      console.error('Error writing .env file:', error)
      throw error
    }
  }

  /**
   * Update specific environment variables in .env file
   */
  updateEnv(updates: Record<string, string | number | boolean | null | undefined>): void {
    // Read existing env
    const existing = this.readEnv()
    
    // Merge with updates
    const merged = { ...existing, ...updates }
    
    // Remove null/undefined values
    for (const key in merged) {
      if (merged[key] === null || merged[key] === undefined) {
        delete merged[key]
      }
    }
    
    // Write back
    this.writeEnv(merged)
  }

  /**
   * Get a specific environment variable
   */
  get(key: string): string | undefined {
    const env = this.readEnv()
    return env[key]
  }

  /**
   * Set a specific environment variable
   */
  set(key: string, value: string | number | boolean | null | undefined): void {
    this.updateEnv({ [key]: value })
  }

  /**
   * Check if .env file exists
   */
  exists(): boolean {
    return existsSync(this.envPath)
  }
}

// Global instance
export const envFile = new EnvFileManager()

// Convenience functions for easier imports
export function readEnvFile(): Record<string, string> {
  return envFile.readEnv()
}

export function writeEnvFile(updates: Record<string, string | boolean | number>): void {
  envFile.updateEnv(updates)
}

export function createEnvFileIfMissing(): void {
  if (!envFile.exists()) {
    envFile.writeEnv({})
  }
}

