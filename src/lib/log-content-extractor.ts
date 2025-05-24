// Interface for log type patterns from the log configurator
interface LogType {
  id: string;
  name: string;
  pattern: string;
  description: string;
  level: string;
}

interface LogItem {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  logTypeId?: string;
}

/**
 * Extract content from log message using the matched log type pattern
 * This removes the pattern text and keeps only the dynamic content
 */
export function extractContentFromLog(
  item: LogItem, 
  logTypes: LogType[]
): string {
  if (!item.logTypeId || !item.message) return item.title || item.message;
  
  // Find the matching log type in the logTypes array
  const logType = logTypes.find(lt => lt.id === item.logTypeId);
  if (!logType || !logType.pattern) return item.title || item.message;
  
  try {
    // Split the pattern by (.*?) to get the fixed text parts that should be removed
    const patternParts = logType.pattern.split(/\(\.\*\?\)/);
    
    // If there are no wildcards, return the original message
    if (patternParts.length <= 1) return item.title || item.message;
    
    let result = item.message;
    
    // Remove each fixed text part from the message
    for (const part of patternParts) {
      if (part.trim().length === 0) continue;
      
      // Unescape the regex pattern part to get the literal text
      let literalPart = part
        .replace(/\\n/g, '\n')
        .replace(/\\r/g, '\r')
        .replace(/\\t/g, '\t')
        .replace(/\\(.)/g, '$1'); // Remove escape characters for special regex chars
      
      // Remove this literal part from the result
      const escapedPart = literalPart.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
      result = result.replace(new RegExp(escapedPart, 'gi'), ' ');
    }
    
    // Clean up the result by removing extra whitespace
    result = result
      .replace(/\s+/g, ' ')  // Replace multiple spaces with single space
      .trim();               // Remove leading/trailing whitespace
    
    // If we have meaningful content left, return it; otherwise return original
    if (result && result.length > 0) {
      return result;
    }
    
    return item.title || item.message;
    
  } catch (error) {
    console.error('Error extracting content from log:', error);
    return item.title || item.message;
  }
}

/**
 * Fetch log types from the configuration
 */
export async function fetchLogTypes(): Promise<LogType[]> {
  try {
    const response = await fetch('/api/logs/config');
    if (response.ok) {
      const configData = await response.json();
      return configData.logTypes || [];
    }
  } catch (error) {
    console.error('Error fetching log types:', error);
  }
  return [];
} 