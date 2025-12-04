import { readFile } from 'fs/promises'
import { join } from 'path'

interface Movie {
  title: string
  title_original: string
  year: number
  release_date?: string
  sources: {
    franchises?: {
      franchise_name: string
      franchise_url: string
    }
    boxofficemojo?: {
      franchise_name: string
      franchise_url: string
    }
  }
  trakt?: {
    trakt_id: number
    title: string
    year: number
    genres?: string[]
  }
}

interface CollectionMetadata {
  franchise_name: string
  franchise_url?: string
  total_movies: number
  years: number[]
}

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const franchiseNames = (query.names as string)?.split(',').map(name => decodeURIComponent(name)) || []
    
    if (!franchiseNames.length || franchiseNames.length > 100) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Provide 1-100 franchise names as comma-separated values in "names" query param'
      })
    }
    
    const unifiedJsonPath = join(process.cwd(), 'data', 'unified.json')
    
    // Check if file exists
    let fileContent: string
    try {
      fileContent = await readFile(unifiedJsonPath, 'utf-8')
    } catch (error: any) {
      if (error.code === 'ENOENT') {
        throw createError({
          statusCode: 404,
          statusMessage: 'Collections data not available. unified.json file is missing.'
        })
      }
      throw error
    }
    
    const data = JSON.parse(fileContent)
    
    const movies: Movie[] = data.movies || []
    
    // Create a map for fast lookup
    const franchiseMap = new Map<string, CollectionMetadata>()
    
    // Initialize all requested franchises
    for (const franchiseName of franchiseNames) {
      franchiseMap.set(franchiseName, {
        franchise_name: franchiseName,
        franchise_url: undefined,
        total_movies: 0,
        years: []
      })
    }
    
    // Process all movies in one pass
    for (const movie of movies) {
      const movieFranchiseName = movie.sources?.franchises?.franchise_name || 
                                 movie.sources?.boxofficemojo?.franchise_name
      
      if (movieFranchiseName && franchiseMap.has(movieFranchiseName)) {
        const metadata = franchiseMap.get(movieFranchiseName)!
        metadata.total_movies++
        
        // Set franchise URL from first movie found
        if (!metadata.franchise_url) {
          metadata.franchise_url = movie.sources?.franchises?.franchise_url || 
                                   movie.sources?.boxofficemojo?.franchise_url
        }
        
        // Add year if not already present
        if (movie.year && !metadata.years.includes(movie.year)) {
          metadata.years.push(movie.year)
        }
      }
    }
    
    // Sort years for each collection
    for (const metadata of franchiseMap.values()) {
      metadata.years.sort((a, b) => a - b)
    }
    
    // Return results in the same order as requested
    const results = franchiseNames
      .map(name => franchiseMap.get(name))
      .filter((metadata): metadata is CollectionMetadata => metadata !== undefined)
    
    return {
      success: true,
      data: {
        collections: results
      }
    }
  } catch (error: any) {
    if (error.statusCode) {
      throw error
    }
    
    console.error('Error reading bulk collection metadata:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to load collection metadata',
      data: { error: error.message }
    })
  }
})

