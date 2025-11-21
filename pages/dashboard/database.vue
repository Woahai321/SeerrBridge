<template>
  <div class="space-y-8">
    <!-- Header Section -->
    <div class="flex items-center justify-between flex-wrap gap-4">
      <div>
        <h1 class="text-3xl font-bold text-foreground tracking-tight">Database Management</h1>
        <p class="text-sm text-muted-foreground mt-1">Monitor database health, explore tables, and run queries</p>
      </div>
      
      <!-- Action Buttons -->
      <div class="flex items-center gap-3">
        <!-- Auto-refresh Toggle -->
        <Button 
          @click="autoRefreshEnabled = !autoRefreshEnabled" 
          :variant="autoRefreshEnabled ? 'default' : 'outline'"
          class="gap-2"
        >
          <AppIcon :icon="autoRefreshEnabled ? 'lucide:play' : 'lucide:pause'" size="18" />
          {{ autoRefreshEnabled ? 'Auto ON' : 'Auto OFF' }}
        </Button>
        
        <!-- Refresh Button -->
        <Button 
          @click="handleRefresh" 
          :disabled="isRefreshing"
          variant="outline"
        >
          <AppIcon v-if="isRefreshing" icon="lucide:loader-2" size="18" class="animate-spin" />
          <AppIcon v-else icon="lucide:refresh-cw" size="18" />
        </Button>
        
        <!-- Clear Database Button -->
        <Button 
          @click="confirmClearDatabase"
          variant="outline"
          class="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200 hover:border-red-300"
        >
          <AppIcon icon="lucide:trash-2" size="18" />
          Clear Database
        </Button>
      </div>
    </div>
    
    <!-- Database Health Overview -->
    <div class="bg-card border border-border rounded-2xl p-6 space-y-6">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold text-foreground">Database Health</h2>
        <div class="flex items-center gap-4">
          <span v-if="lastUpdated" class="text-sm text-muted-foreground flex items-center gap-2">
            <AppIcon icon="lucide:clock" size="16" class="text-blue-500" />
            Last updated: {{ lastUpdated.toLocaleTimeString() }}
          </span>
        </div>
      </div>
      
      <!-- Status Overview -->
      <div class="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Database Status Card -->
        <div class="bg-background border border-border rounded-2xl p-6 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-emerald-500/50 group relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-green-500"></div>
          <div class="flex items-center justify-between mb-3">
            <div class="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
              <AppIcon icon="lucide:check-circle" size="24" class="text-emerald-500" />
            </div>
            <span class="text-xs font-medium text-emerald-500">Status</span>
          </div>
          <p class="text-3xl font-bold text-foreground mb-1">{{ health?.status?.version || 'N/A' }}</p>
          <p class="text-xs text-muted-foreground">Database Version</p>
        </div>
        
        <!-- Database Size Card -->
        <div class="bg-background border border-border rounded-2xl p-6 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-blue-500/50 group relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-500"></div>
          <div class="flex items-center justify-between mb-3">
            <div class="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
              <AppIcon icon="lucide:database" size="24" class="text-blue-500" />
            </div>
            <span class="text-xs font-medium text-blue-500">Size</span>
          </div>
          <p class="text-3xl font-bold text-foreground mb-1">{{ formatBytes(health?.database?.total_data_size + health?.database?.total_index_size) || '0 B' }}</p>
          <p class="text-xs text-muted-foreground">Total Size</p>
        </div>
        
        <!-- Performance Card -->
        <div class="bg-background border border-border rounded-2xl p-6 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-purple-500/50 group relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-pink-500"></div>
          <div class="flex items-center justify-between mb-3">
            <div class="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center group-hover:bg-purple-500/20 transition-colors">
              <AppIcon icon="lucide:trending-up" size="24" class="text-purple-500" />
            </div>
            <span class="text-xs font-medium text-purple-500">{{ Math.round((health?.status?.questions || 0) / 1000) }}K</span>
          </div>
          <p class="text-3xl font-bold text-foreground mb-1">{{ formatNumber(health?.status?.questions || 0) }}</p>
          <p class="text-xs text-muted-foreground">Total Queries</p>
        </div>
      </div>
      
      <!-- Divider -->
      <div class="border-t border-border"></div>
      
      <!-- Detailed Stats -->
      <div class="flex flex-col lg:flex-row gap-4 lg:gap-0">
        <!-- Connection Info -->
        <div class="flex-1 bg-background border border-border rounded-2xl lg:rounded-l-2xl lg:rounded-r-none lg:border-r-0 p-4 shadow-sm hover:shadow-md transition-all">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-emerald-500/10 rounded-xl flex items-center justify-center">
                <AppIcon icon="lucide:users" size="20" class="text-emerald-500" />
              </div>
              <div>
                <h3 class="text-xl font-bold text-foreground">{{ health?.status?.threads_connected || 0 }}</h3>
                <p class="text-xs text-muted-foreground">Active Connections</p>
              </div>
            </div>
            <span class="text-xs font-semibold px-2.5 py-1 bg-emerald-500/10 text-emerald-500 rounded-full">
              {{ Math.round(((health?.status?.threads_connected || 0) / (health?.status?.max_connections || 1)) * 100) }}%
            </span>
          </div>
          
          <div class="grid grid-cols-2 gap-2 pt-3 border-t border-border">
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Max Connections</p>
              <p class="text-base font-bold text-foreground">{{ formatNumber(health?.status?.max_connections || 0) }}</p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Running Threads</p>
              <p class="text-base font-bold text-foreground">{{ formatNumber(health?.status?.threads_running || 0) }}</p>
            </div>
          </div>
        </div>
        
        <!-- Vertical Divider -->
        <div class="hidden lg:block w-px bg-border self-stretch"></div>
        
        <!-- Table Info -->
        <div class="flex-1 bg-background border border-border rounded-2xl lg:rounded-r-2xl lg:rounded-l-none lg:border-l-0 p-4 shadow-sm hover:shadow-md transition-all">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center">
                <AppIcon icon="lucide:table" size="20" class="text-blue-500" />
              </div>
              <div>
                <h3 class="text-xl font-bold text-foreground">{{ health?.database?.total_tables || 0 }}</h3>
                <p class="text-xs text-muted-foreground">Total Tables</p>
              </div>
            </div>
            <span class="text-xs font-semibold px-2.5 py-1 bg-blue-500/10 text-blue-500 rounded-full">
              {{ formatNumber(health?.database?.total_rows || 0) }} rows
            </span>
          </div>
          
          <div class="grid grid-cols-2 gap-2 pt-3 border-t border-border">
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Data Size</p>
              <p class="text-base font-bold text-foreground">{{ formatBytes(health?.database?.total_data_size || 0) }}</p>
            </div>
            <div>
              <p class="text-xs text-muted-foreground mb-0.5">Index Size</p>
              <p class="text-base font-bold text-foreground">{{ formatBytes(health?.database?.total_index_size || 0) }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Navigation Tabs -->
    <div class="bg-card rounded-2xl border border-border overflow-hidden">
      <!-- Tab Navigation -->
      <div class="bg-gradient-to-r from-muted to-muted/50 border-b border-border">
        <nav class="flex space-x-1 p-2">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              activeTab === tab.id
                ? 'bg-background text-primary shadow-lg border border-border'
                : 'text-muted-foreground hover:text-foreground hover:bg-background/50',
              'flex items-center gap-2 px-4 py-3 rounded-lg font-medium text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2'
            ]"
          >
            <AppIcon :icon="tab.icon" size="16" />
            {{ tab.name }}
          </button>
        </nav>
      </div>

      <div class="p-8">
        <!-- Tables Tab -->
        <div v-if="activeTab === 'tables'" class="space-y-6">
          <!-- Section Header -->
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
                <AppIcon icon="lucide:table" size="20" class="text-white" />
              </div>
              <div>
                <h3 class="text-xl font-bold text-foreground">Database Tables</h3>
                <p class="text-sm text-muted-foreground">Manage and explore your database tables</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <Button
                @click="refreshTables"
                :disabled="loadingTables || isRefreshing"
                variant="outline"
                class="gap-2"
              >
                <AppIcon icon="lucide:refresh-cw" size="18" :class="{ 'animate-spin': loadingTables || isRefreshing }" />
                {{ loadingTables || isRefreshing ? 'Refreshing...' : 'Refresh Tables' }}
              </Button>
            </div>
          </div>

          <!-- Loading State -->
          <div v-if="loadingTables" class="flex items-center justify-center py-24">
            <div class="text-center">
              <div class="w-20 h-20 mx-auto mb-6 bg-primary/10 rounded-2xl flex items-center justify-center">
                <AppIcon icon="lucide:loader-2" size="40" class="text-primary animate-spin" />
              </div>
              <h3 class="text-xl font-semibold text-foreground mb-2">Loading tables</h3>
              <p class="text-sm text-muted-foreground">Please wait while we fetch your database tables</p>
            </div>
          </div>

          <!-- Empty State -->
          <div v-else-if="tables.length === 0 && !loadingTables" class="text-center py-24">
            <div class="inline-flex w-24 h-24 mb-6 bg-muted rounded-3xl items-center justify-center">
              <AppIcon icon="lucide:table" size="48" class="text-muted-foreground" />
            </div>
            <h3 class="text-2xl font-bold text-foreground mb-3">No tables found</h3>
            <p class="text-muted-foreground mb-8 max-w-md mx-auto">
              This might indicate a database connection issue or the database is empty.
            </p>
            <Button @click="loadTables" class="gap-2">
              <AppIcon icon="lucide:refresh-cw" size="18" />
              Retry Loading
            </Button>
          </div>

          <!-- Tables Grid -->
          <div v-else class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            <div
              v-for="table in tables"
              :key="table.name"
              @click="viewTableData(table.name)"
              class="group relative bg-card rounded-2xl overflow-hidden cursor-pointer transition-all hover:shadow-2xl hover:-translate-y-2 border border-border"
            >
              <!-- Table Header -->
              <div class="p-6 space-y-4">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <div class="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
                      <AppIcon icon="lucide:table" size="24" class="text-blue-500" />
                    </div>
                    <div>
                      <h4 class="text-lg font-bold text-foreground">{{ table.name }}</h4>
                      <p class="text-sm text-muted-foreground">{{ table.engine }}</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200">
                      {{ formatNumber(table.row_count) }} rows
                    </span>
                  </div>
                </div>
                
                <div class="space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-muted-foreground">Size</span>
                    <span class="text-sm font-semibold text-foreground">{{ formatBytes(table.total_size) }}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-sm text-muted-foreground">Engine</span>
                    <span class="text-sm font-semibold text-foreground">{{ table.engine }}</span>
                  </div>
                </div>
                
                <!-- Action Buttons -->
                <div class="flex items-center gap-2 pt-2">
                  <Button
                    @click.stop="viewTableData(table.name)"
                    size="sm"
                    class="flex-1 gap-2"
                  >
                    <AppIcon icon="lucide:table" size="16" />
                    View Data
                  </Button>
                  <Button
                    @click.stop="viewTableStructure(table.name)"
                    size="sm"
                    variant="outline"
                    class="flex-1 gap-2"
                  >
                    <AppIcon icon="lucide:database" size="16" />
                    View Structure
                  </Button>
                  <Button
                    @click.stop="confirmClearTable(table.name, table.row_count)"
                    variant="outline"
                    size="sm"
                    class="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200 hover:border-red-300"
                  >
                    <AppIcon icon="lucide:trash-2" size="16" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Data Viewer Tab -->
        <div v-if="activeTab === 'data'" class="space-y-6">
          <!-- Section Header -->
          <div class="flex items-center gap-3">
            <div class="p-2 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-lg">
              <AppIcon icon="lucide:eye" size="20" class="text-white" />
            </div>
            <div>
              <h3 class="text-xl font-bold text-foreground">Table Data Viewer</h3>
              <p class="text-sm text-muted-foreground">Select a table from the Tables tab to view its data</p>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="!selectedDataTable" class="text-center py-24">
            <div class="inline-flex w-24 h-24 mb-6 bg-muted rounded-3xl items-center justify-center">
              <AppIcon icon="lucide:table" size="48" class="text-muted-foreground" />
            </div>
            <h3 class="text-2xl font-bold text-foreground mb-3">No Table Selected</h3>
            <p class="text-muted-foreground mb-8 max-w-md mx-auto">
              Go to the Tables tab and click "View Data" on any table to start browsing data
            </p>
            <Button @click="activeTab = 'tables'" class="gap-2">
              <AppIcon icon="lucide:arrow-left" size="18" />
              Go to Tables
            </Button>
          </div>

          <!-- Data Viewer Content -->
          <div v-else class="space-y-6">
            <!-- Table Header -->
            <div class="bg-card border border-border rounded-2xl p-6">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                  <div class="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center">
                    <AppIcon icon="lucide:table" size="24" class="text-emerald-500" />
                  </div>
                  <div>
                    <h4 class="text-xl font-bold text-foreground">{{ selectedDataTable }}</h4>
                    <p class="text-sm text-muted-foreground">Table Data Viewer</p>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <Button
                    @click="loadTableData"
                    :disabled="loadingTableData"
                    variant="outline"
                    class="gap-2"
                  >
                    <AppIcon icon="lucide:refresh-cw" size="18" :class="{ 'animate-spin': loadingTableData }" />
                    Refresh
                  </Button>
                  <div class="flex items-center gap-2">
                    <Button
                      @click="exportTableData('csv')"
                      variant="outline"
                      size="sm"
                      class="gap-2"
                    >
                      <AppIcon icon="lucide:download" size="16" />
                      CSV
                    </Button>
                    <Button
                      @click="exportTableData('json')"
                      variant="outline"
                      size="sm"
                      class="gap-2"
                    >
                      <AppIcon icon="lucide:download" size="16" />
                      JSON
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Search and Controls -->
            <div class="bg-card border border-border rounded-2xl p-6">
              <div class="flex flex-col sm:flex-row gap-4">
                <div class="flex-1">
                  <label class="block text-sm font-semibold text-foreground mb-2">
                    <div class="flex items-center gap-2">
                      <AppIcon icon="lucide:search" size="16" />
                      Search Data
                    </div>
                  </label>
                  <div class="flex">
                    <input
                      v-model="dataSearch"
                      @keyup.enter="searchTableData"
                      type="text"
                      placeholder="Search across all columns..."
                      class="flex-1 px-4 py-3 border border-input rounded-l-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring bg-background text-foreground"
                    />
                    <Button
                      @click="searchTableData"
                      class="rounded-l-none"
                    >
                      <AppIcon icon="lucide:search" size="18" />
                    </Button>
                  </div>
                </div>
                <div class="sm:w-48">
                  <label class="block text-sm font-semibold text-foreground mb-2">
                    <div class="flex items-center gap-2">
                      <AppIcon icon="lucide:sliders-horizontal" size="16" />
                      Rows per page
                    </div>
                  </label>
                  <select
                    v-model="dataLimit"
                    @change="loadTableData"
                    class="w-full px-3 py-3 border border-input rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring bg-background text-foreground"
                  >
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                    <option value="200">200</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Data Table -->
            <div v-if="loadingTableData" class="flex items-center justify-center py-24">
              <div class="text-center">
                <div class="w-20 h-20 mx-auto mb-6 bg-primary/10 rounded-2xl flex items-center justify-center">
                  <AppIcon icon="lucide:loader-2" size="40" class="text-primary animate-spin" />
                </div>
                <h3 class="text-xl font-semibold text-foreground mb-2">Loading data</h3>
                <p class="text-sm text-muted-foreground">Please wait while we fetch table data</p>
              </div>
            </div>

            <div v-else-if="tableData && tableData.data.length === 0" class="text-center py-24">
              <div class="inline-flex w-24 h-24 mb-6 bg-muted rounded-3xl items-center justify-center">
                <AppIcon icon="lucide:table" size="48" class="text-muted-foreground" />
              </div>
              <h3 class="text-2xl font-bold text-foreground mb-3">No data found</h3>
              <p class="text-muted-foreground mb-8 max-w-md mx-auto">
                {{ dataSearch ? 'Try adjusting your search criteria' : 'This table appears to be empty' }}
              </p>
            </div>

            <div v-else-if="tableData" class="space-y-6">
              <!-- Data Info -->
              <div class="bg-card border border-border rounded-2xl p-4">
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div class="flex items-center gap-3">
                    <AppIcon icon="lucide:info" size="20" class="text-blue-500" />
                    <span class="text-sm font-medium text-foreground">
                      Showing {{ ((tableData.page - 1) * tableData.limit) + 1 }} to 
                      {{ Math.min(tableData.page * tableData.limit, tableData.total) }} of 
                      {{ tableData.total }} rows
                    </span>
                  </div>
                  <div v-if="dataSearch" class="flex items-center gap-2 text-sm text-muted-foreground">
                    <AppIcon icon="lucide:filter" size="16" />
                    <span>Filtered by "{{ dataSearch }}"</span>
                  </div>
                </div>
              </div>

              <!-- Data Table -->
              <div class="bg-card border border-border rounded-2xl overflow-hidden">
                <div class="overflow-x-auto">
                  <table class="min-w-full divide-y divide-border">
                    <thead class="bg-muted">
                      <tr>
                        <th
                          v-for="column in dataColumns"
                          :key="column"
                          @click="sortTableData(column)"
                          class="px-6 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider cursor-pointer hover:bg-muted/80 transition-colors"
                        >
                          <div class="flex items-center space-x-2">
                            <AppIcon icon="lucide:tag" size="12" />
                            <span>{{ column }}</span>
                            <AppIcon
                              v-if="dataSortBy === column"
                              :icon="dataSortOrder === 'ASC' ? 'lucide:chevron-up' : 'lucide:chevron-down'"
                              size="12"
                            />
                          </div>
                        </th>
                      </tr>
                    </thead>
                    <tbody class="bg-card divide-y divide-border">
                      <tr v-for="(row, index) in tableData.data" :key="index" class="hover:bg-muted/50 transition-colors">
                        <td
                          v-for="column in dataColumns"
                          :key="column"
                          class="px-6 py-4 text-sm text-foreground font-mono"
                        >
                          <span class="truncate block max-w-xs" :title="formatValue(row[column])">
                            {{ formatValue(row[column]) }}
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Pagination -->
              <div v-if="tableData.totalPages > 1" class="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div class="flex items-center space-x-2">
                  <Button
                    @click="changeDataPage(tableData.page - 1)"
                    :disabled="tableData.page <= 1"
                    variant="outline"
                    size="sm"
                    class="gap-2"
                  >
                    <AppIcon icon="lucide:chevron-left" size="16" />
                    Previous
                  </Button>
                  
                  <div class="flex space-x-1">
                    <Button
                      v-for="page in Math.min(5, tableData.totalPages)"
                      :key="page"
                      @click="changeDataPage(page)"
                      :variant="page === tableData.page ? 'default' : 'outline'"
                      size="sm"
                    >
                      {{ page }}
                    </Button>
                  </div>
                  
                  <Button
                    @click="changeDataPage(tableData.page + 1)"
                    :disabled="tableData.page >= tableData.totalPages"
                    variant="outline"
                    size="sm"
                    class="gap-2"
                  >
                    Next
                    <AppIcon icon="lucide:chevron-right" size="16" />
                  </Button>
                </div>
                
                <div class="text-sm text-muted-foreground">
                  Page {{ tableData.page }} of {{ tableData.totalPages }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Query Interface Tab -->
        <div v-if="activeTab === 'query'" class="space-y-6">
          <!-- Section Header -->
          <div class="flex items-center gap-3">
            <div class="p-2 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg">
              <AppIcon icon="lucide:code" size="20" class="text-white" />
            </div>
            <div>
              <h3 class="text-xl font-bold text-foreground">SQL Query Interface</h3>
              <p class="text-sm text-muted-foreground">Execute custom SQL queries against your database</p>
            </div>
          </div>

          <!-- Query Input Section -->
          <div class="bg-card border border-border rounded-2xl p-6 shadow-lg">
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <label class="block text-sm font-semibold text-foreground">
                  <div class="flex items-center gap-2">
                    <AppIcon icon="lucide:code" size="16" />
                    SQL Query
                  </div>
                </label>
                <div class="text-xs text-muted-foreground">
                  {{ queryText.length }} characters
                </div>
              </div>
              
              <textarea
                v-model="queryText"
                rows="6"
                placeholder="Enter your SQL query here..."
                class="w-full px-4 py-3 border border-input rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring bg-background text-foreground font-mono text-sm resize-none"
              ></textarea>
              
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                  <div class="flex items-center gap-2">
                    <label class="text-sm font-medium text-foreground">Limit Results:</label>
                    <input
                      v-model.number="queryLimit"
                      type="number"
                      min="1"
                      max="1000"
                      class="w-20 px-3 py-1 border border-input rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring bg-background text-foreground text-sm"
                    />
                  </div>
                </div>
                
                <div class="flex items-center gap-3">
                  <Button
                    @click="clearQuery"
                    variant="outline"
                    class="gap-2"
                  >
                    <AppIcon icon="lucide:x" size="16" />
                    Clear
                  </Button>
                  <Button
                    @click="executeQuery"
                    :disabled="!queryText.trim() || executingQuery"
                    class="gap-2"
                  >
                    <AppIcon icon="lucide:play" size="16" :class="{ 'animate-pulse': executingQuery }" />
                    {{ executingQuery ? 'Executing...' : 'Execute Query' }}
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <!-- Query Results Section -->
          <div v-if="queryResult" class="bg-card border border-border rounded-2xl overflow-hidden shadow-lg">
            <!-- Results Header -->
            <div class="bg-gradient-to-r from-muted to-muted/50 border-b border-border px-6 py-4">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <AppIcon icon="lucide:chart-bar" size="20" class="text-emerald-500" />
                  <h4 class="text-lg font-semibold text-foreground">
                    Query Results
                  </h4>
                </div>
                <div class="flex items-center gap-4 text-sm">
                  <span class="text-muted-foreground">
                    <span class="font-semibold">{{ queryResult.rowCount }}</span> rows returned
                  </span>
                  <span class="text-muted-foreground">
                    Executed in <span class="font-semibold">{{ queryResult.executionTime }}ms</span>
                  </span>
                </div>
              </div>
            </div>

            <!-- Results Table -->
            <div v-if="queryResult.data && queryResult.data.length > 0" class="overflow-x-auto">
              <table class="min-w-full divide-y divide-border">
                <thead class="bg-muted">
                  <tr>
                    <th
                      v-for="column in queryResult.columns"
                      :key="column"
                      class="px-6 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider"
                    >
                      <div class="flex items-center gap-2">
                        <AppIcon icon="lucide:tag" size="12" />
                        {{ column }}
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-card divide-y divide-border">
                  <tr v-for="(row, index) in queryResult.data" :key="index" class="hover:bg-muted/50 transition-colors">
                    <td
                      v-for="column in queryResult.columns"
                      :key="column"
                      class="px-6 py-4 text-sm text-foreground font-mono"
                    >
                      <span class="truncate block max-w-xs" :title="formatValue(row[column])">
                        {{ formatValue(row[column]) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Empty Results -->
            <div v-else class="flex flex-col items-center justify-center py-12">
              <div class="p-4 bg-blue-100 dark:bg-blue-900/20 rounded-full mb-4">
                <AppIcon icon="lucide:info" size="32" class="text-blue-500" />
              </div>
              <h5 class="text-lg font-semibold text-foreground mb-2">No Results</h5>
              <p class="text-muted-foreground text-center">
                The query executed successfully but returned no data.
              </p>
            </div>
          </div>

          <!-- Query Error -->
          <div v-if="queryError" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6">
            <div class="flex items-start gap-3">
              <AppIcon icon="lucide:alert-triangle" size="24" class="text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <h4 class="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">Query Error</h4>
                <p class="text-red-700 dark:text-red-300 font-mono text-sm">{{ queryError }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Clear Table Modal -->
    <div v-if="showClearTableModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-gray-900/50 backdrop-blur-sm transition-opacity" @click="showClearTableModal = false"></div>
        
        <!-- Modal panel -->
        <div class="relative bg-card rounded-2xl shadow-xl border border-border max-w-md w-full transform transition-all">
          <!-- Modal header -->
          <div class="p-6 border-b border-border">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 bg-red-500/10 rounded-xl flex items-center justify-center">
                  <AppIcon icon="lucide:alert-triangle" size="24" class="text-red-500" />
                </div>
                <div>
                  <h3 class="text-xl font-bold text-foreground">Clear Table</h3>
                  <p class="text-sm text-muted-foreground">This action cannot be undone</p>
                </div>
              </div>
              <Button @click="showClearTableModal = false" variant="ghost" class="p-2">
                <AppIcon icon="lucide:x" size="20" />
              </Button>
            </div>
          </div>
          
          <!-- Modal body -->
          <div class="p-6 space-y-4">
            <p class="text-foreground">
              Are you sure you want to clear all data from the table <span class="font-semibold text-red-500">{{ selectedTableName }}</span>?
            </p>
            <p class="text-sm text-muted-foreground">
              This will permanently delete all data from this table and cannot be undone.
            </p>
            
            <div class="space-y-2">
              <label class="block text-sm font-semibold text-foreground">
                Type <span class="font-mono text-red-500">CLEAR</span> to confirm:
              </label>
              <input
                v-model="clearTableConfirmText"
                type="text"
                placeholder="Enter CLEAR to confirm"
                class="w-full px-4 py-3 border border-input rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-background text-foreground"
                @keyup.enter="handleClearTableEnter"
              />
            </div>
          </div>
          
          <!-- Modal footer -->
          <div class="p-6 border-t border-border flex items-center gap-3">
            <Button
              @click="showClearTableModal = false"
              variant="outline"
              class="flex-1"
            >
              Cancel
            </Button>
            <Button
              @click="clearTable()"
              :disabled="clearTableConfirmText !== 'CLEAR' || clearingTable"
              variant="destructive"
              class="flex-1 gap-2"
            >
              <AppIcon v-if="clearingTable" icon="lucide:loader-2" size="18" class="animate-spin" />
              <AppIcon v-else icon="lucide:trash-2" size="18" />
              {{ clearingTable ? 'Clearing...' : 'Clear Table' }}
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Clear Database Modal -->
    <div v-if="showClearDatabaseModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-gray-900/50 backdrop-blur-sm transition-opacity" @click="showClearDatabaseModal = false"></div>
        
        <!-- Modal panel -->
        <div class="relative bg-card rounded-2xl shadow-xl border border-border max-w-md w-full transform transition-all">
          <!-- Modal header -->
          <div class="p-6 border-b border-border">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 bg-red-500/10 rounded-xl flex items-center justify-center">
                  <AppIcon icon="lucide:alert-triangle" size="24" class="text-red-500" />
                </div>
                <div>
                  <h3 class="text-xl font-bold text-foreground">Clear Database</h3>
                  <p class="text-sm text-muted-foreground">This action cannot be undone</p>
                </div>
              </div>
              <Button @click="showClearDatabaseModal = false" variant="ghost" class="p-2">
                <AppIcon icon="lucide:x" size="20" />
              </Button>
            </div>
          </div>
          
          <!-- Modal body -->
          <div class="p-6 space-y-4">
            <p class="text-foreground font-semibold">
              ⚠️ DANGER: This will clear ALL data from ALL tables in the database!
            </p>
            <p class="text-sm text-muted-foreground">
              This will permanently delete all data from the entire database and cannot be undone. All tables will be emptied.
            </p>
            
            <div class="space-y-2">
              <label class="block text-sm font-semibold text-foreground">
                Type <span class="font-mono text-red-500">WIPE_DATABASE</span> to confirm:
              </label>
              <input
                v-model="clearDatabaseConfirmText"
                type="text"
                placeholder="Enter WIPE_DATABASE to confirm"
                class="w-full px-4 py-3 border border-input rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-background text-foreground"
                @keyup.enter="handleClearDatabaseEnter"
              />
            </div>
          </div>
          
          <!-- Modal footer -->
          <div class="p-6 border-t border-border flex items-center gap-3">
            <Button
              @click="showClearDatabaseModal = false"
              variant="outline"
              class="flex-1"
            >
              Cancel
            </Button>
            <Button
              @click="clearDatabase()"
              :disabled="clearDatabaseConfirmText !== 'WIPE_DATABASE' || clearingDatabase"
              variant="destructive"
              class="flex-1 gap-2"
            >
              <AppIcon v-if="clearingDatabase" icon="lucide:loader-2" size="18" class="animate-spin" />
              <AppIcon v-else icon="lucide:trash-2" size="18" />
              {{ clearingDatabase ? 'Clearing...' : 'Clear Database' }}
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Table Structure Modal -->
    <div v-if="showStructureModal" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-gray-900/50 backdrop-blur-sm transition-opacity" @click="showStructureModal = false"></div>
        
        <!-- Modal panel -->
        <div class="relative bg-card rounded-2xl shadow-xl border border-border max-w-4xl w-full transform transition-all max-h-[90vh] overflow-hidden flex flex-col">
          <!-- Modal header -->
          <div class="p-6 border-b border-border flex-shrink-0">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center">
                  <AppIcon icon="lucide:database" size="24" class="text-blue-500" />
                </div>
                <div>
                  <h3 class="text-xl font-bold text-foreground">Table Structure</h3>
                  <p class="text-sm text-muted-foreground">{{ selectedStructureTable }}</p>
                </div>
              </div>
              <Button @click="showStructureModal = false" variant="ghost" class="p-2">
                <AppIcon icon="lucide:x" size="20" />
              </Button>
            </div>
          </div>
          
          <!-- Modal body -->
          <div class="p-6 overflow-y-auto flex-1">
            <!-- Loading State -->
            <div v-if="loadingStructure" class="flex items-center justify-center py-12">
              <div class="text-center">
                <div class="w-16 h-16 mx-auto mb-4 bg-primary/10 rounded-2xl flex items-center justify-center">
                  <AppIcon icon="lucide:loader-2" size="32" class="text-primary animate-spin" />
                </div>
                <p class="text-sm text-muted-foreground">Loading table structure...</p>
              </div>
            </div>

            <!-- Structure Content -->
            <div v-else-if="tableStructure" class="space-y-6">
              <!-- Columns Section -->
              <div class="space-y-4">
                <div class="flex items-center gap-2">
                  <AppIcon icon="lucide:columns" size="20" class="text-blue-500" />
                  <h4 class="text-lg font-semibold text-foreground">Columns</h4>
                  <span class="text-sm text-muted-foreground">({{ tableStructure.columns?.length || 0 }})</span>
                </div>
                
                <div class="bg-background border border-border rounded-xl overflow-hidden">
                  <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-border">
                      <thead class="bg-muted">
                        <tr>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Name</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Type</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Nullable</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Default</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Key</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Extra</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Comment</th>
                        </tr>
                      </thead>
                      <tbody class="bg-card divide-y divide-border">
                        <tr v-for="(column, index) in tableStructure.columns" :key="index" class="hover:bg-muted/50 transition-colors">
                          <td class="px-4 py-3 text-sm font-semibold text-foreground font-mono">{{ column.name }}</td>
                          <td class="px-4 py-3 text-sm text-foreground">
                            <span class="font-mono">{{ column.type }}</span>
                            <span v-if="column.max_length" class="text-muted-foreground">({{ column.max_length }})</span>
                            <span v-else-if="column.precision && column.scale" class="text-muted-foreground">
                              ({{ column.precision }},{{ column.scale }})
                            </span>
                          </td>
                          <td class="px-4 py-3 text-sm text-foreground">
                            <span :class="column.nullable === 'YES' ? 'text-amber-500' : 'text-emerald-500'">
                              {{ column.nullable === 'YES' ? 'YES' : 'NO' }}
                            </span>
                          </td>
                          <td class="px-4 py-3 text-sm text-foreground font-mono">
                            <span v-if="column.default_value !== null && column.default_value !== undefined">
                              {{ column.default_value }}
                            </span>
                            <span v-else class="text-muted-foreground">—</span>
                          </td>
                          <td class="px-4 py-3 text-sm text-foreground">
                            <span v-if="column.key === 'PRI'" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200">
                              PRIMARY
                            </span>
                            <span v-else-if="column.key === 'UNI'" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
                              UNIQUE
                            </span>
                            <span v-else-if="column.key === 'MUL'" class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
                              INDEX
                            </span>
                            <span v-else class="text-muted-foreground">—</span>
                          </td>
                          <td class="px-4 py-3 text-sm text-foreground">
                            <span v-if="column.extra" class="text-amber-500 font-mono">{{ column.extra }}</span>
                            <span v-else class="text-muted-foreground">—</span>
                          </td>
                          <td class="px-4 py-3 text-sm text-muted-foreground">
                            {{ column.comment || '—' }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- Indexes Section -->
              <div v-if="tableStructure.indexes && tableStructure.indexes.length > 0" class="space-y-4">
                <div class="flex items-center gap-2">
                  <AppIcon icon="lucide:key" size="20" class="text-purple-500" />
                  <h4 class="text-lg font-semibold text-foreground">Indexes</h4>
                  <span class="text-sm text-muted-foreground">({{ tableStructure.indexes.length }})</span>
                </div>
                
                <div class="bg-background border border-border rounded-xl overflow-hidden">
                  <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-border">
                      <thead class="bg-muted">
                        <tr>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Index Name</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Column</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Unique</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Type</th>
                          <th class="px-4 py-3 text-left text-xs font-semibold text-foreground uppercase tracking-wider">Cardinality</th>
                        </tr>
                      </thead>
                      <tbody class="bg-card divide-y divide-border">
                        <tr v-for="(index, indexIdx) in tableStructure.indexes" :key="indexIdx" class="hover:bg-muted/50 transition-colors">
                          <td class="px-4 py-3 text-sm font-semibold text-foreground font-mono">{{ index.name }}</td>
                          <td class="px-4 py-3 text-sm text-foreground font-mono">{{ index.column_name }}</td>
                          <td class="px-4 py-3 text-sm text-foreground">
                            <span :class="index.non_unique === 0 ? 'text-emerald-500' : 'text-muted-foreground'">
                              {{ index.non_unique === 0 ? 'YES' : 'NO' }}
                            </span>
                          </td>
                          <td class="px-4 py-3 text-sm text-foreground font-mono">{{ index.type }}</td>
                          <td class="px-4 py-3 text-sm text-foreground">
                            {{ index.cardinality ? formatNumber(index.cardinality) : '—' }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- No Indexes Message -->
              <div v-else class="text-center py-8 text-muted-foreground">
                <AppIcon icon="lucide:info" size="20" class="inline-block mb-2" />
                <p class="text-sm">No indexes defined for this table</p>
              </div>
            </div>

            <!-- Error State -->
            <div v-else class="flex items-center justify-center py-12">
              <div class="text-center">
                <div class="w-16 h-16 mx-auto mb-4 bg-red-500/10 rounded-2xl flex items-center justify-center">
                  <AppIcon icon="lucide:alert-triangle" size="32" class="text-red-500" />
                </div>
                <p class="text-sm text-red-500">Failed to load table structure</p>
              </div>
            </div>
          </div>
          
          <!-- Modal footer -->
          <div class="p-6 border-t border-border flex-shrink-0 flex items-center justify-end gap-3">
            <Button
              @click="showStructureModal = false"
              variant="outline"
            >
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from '~/components/ui/Button.vue'
import { ref, onMounted, onUnmounted } from 'vue'

// Meta
useHead({
  title: 'Database Management - SeerrBridge'
})

// State
const activeTab = ref('tables')
const health = ref(null)
const tables = ref([])
const loadingTables = ref(false)
const loadingTableData = ref(false)
const isRefreshing = ref(false)
const autoRefreshEnabled = ref(true)
const lastUpdated = ref(null)

// Data viewer state
const selectedDataTable = ref(null)
const tableData = ref(null)
const dataColumns = ref([])
const dataPage = ref(1)
const dataLimit = ref(25)
const dataSearch = ref('')
const dataSortBy = ref('')
const dataSortOrder = ref('ASC')

// Query interface state
const queryText = ref('')
const queryLimit = ref(100)
const queryResult = ref(null)
const queryError = ref(null)
const executingQuery = ref(false)

// Clear table state
const selectedTableName = ref(null)
const clearingTable = ref(false)
const showClearTableModal = ref(false)
const clearTableConfirmText = ref('')

// Clear database state
const clearingDatabase = ref(false)
const showClearDatabaseModal = ref(false)
const clearDatabaseConfirmText = ref('')

// Table structure modal state
const showStructureModal = ref(false)
const tableStructure = ref(null)
const loadingStructure = ref(false)
const selectedStructureTable = ref(null)

const tabs = [
  { id: 'tables', name: 'Tables', icon: 'lucide:table' },
  { id: 'data', name: 'Data Viewer', icon: 'lucide:eye' },
  { id: 'query', name: 'Query Interface', icon: 'lucide:code' }
]

// Methods
const formatUptime = (seconds) => {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else {
    return `${minutes}m`
  }
}

const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatNumber = (num) => {
  return new Intl.NumberFormat().format(num)
}

const formatValue = (value) => {
  if (value === null || value === undefined) return 'NULL'
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const loadHealth = async () => {
  try {
    const response = await $fetch('/api/database/health')
    health.value = response
    lastUpdated.value = new Date()
  } catch (error) {
    console.error('Error loading health:', error)
  }
}

const loadTables = async () => {
  loadingTables.value = true
  try {
    const response = await $fetch('/api/database/tables')
    tables.value = response.tables || []
  } catch (error) {
    console.error('Error loading tables:', error)
  } finally {
    loadingTables.value = false
  }
}

const refreshTables = async () => {
  await loadTables()
}

const handleRefresh = async () => {
  isRefreshing.value = true
  try {
    await Promise.all([
      loadHealth(),
      loadTables()
    ])
  } finally {
    isRefreshing.value = false
  }
}

const viewTableData = async (tableName) => {
  selectedDataTable.value = tableName
  activeTab.value = 'data'
  dataPage.value = 1
  dataSearch.value = ''
  dataSortBy.value = ''
  dataSortOrder.value = 'ASC'
  await loadTableData()
}

const loadTableData = async () => {
  if (!selectedDataTable.value) return
  
  loadingTableData.value = true
  
  try {
    const params = new URLSearchParams({
      page: dataPage.value.toString(),
      limit: dataLimit.value.toString()
    })
    
    if (dataSearch.value) params.append('search', dataSearch.value)
    if (dataSortBy.value) {
      params.append('sortBy', dataSortBy.value)
      params.append('sortOrder', dataSortOrder.value)
    }
    
    params.append('table', selectedDataTable.value)
    const response = await $fetch(`/api/database/table-data?${params.toString()}`)
    
    tableData.value = response
    if (response.data && response.data.length > 0) {
      dataColumns.value = Object.keys(response.data[0])
    }
  } catch (error) {
    console.error('Error loading table data:', error)
  } finally {
    loadingTableData.value = false
  }
}

const searchTableData = () => {
  dataPage.value = 1
  loadTableData()
}

const sortTableData = (column) => {
  if (dataSortBy.value === column) {
    dataSortOrder.value = dataSortOrder.value === 'ASC' ? 'DESC' : 'ASC'
  } else {
    dataSortBy.value = column
    dataSortOrder.value = 'ASC'
  }
  dataPage.value = 1
  loadTableData()
}

const changeDataPage = (page) => {
  dataPage.value = page
  loadTableData()
}

const exportTableData = async (format) => {
  if (!selectedDataTable.value) return
  
  try {
    const response = await $fetch(`/api/database/export-data?table=${selectedDataTable.value}&format=${format}`)
    
    const blob = new Blob([response], { type: format === 'csv' ? 'text/csv' : 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedDataTable.value}.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Error exporting table data:', error)
  }
}

const executeQuery = async () => {
  if (!queryText.value.trim()) return
  
  executingQuery.value = true
  queryError.value = null
  queryResult.value = null
  
  try {
    const response = await $fetch('/api/database/query', {
      method: 'POST',
      body: {
        query: queryText.value,
        limit: queryLimit.value
      }
    })
    
    queryResult.value = response
  } catch (error) {
    queryError.value = error.data?.message || 'Query execution failed'
  } finally {
    executingQuery.value = false
  }
}

let refreshInterval = null

const startAutoRefresh = () => {
  if (refreshInterval) return
  
  refreshInterval = setInterval(async () => {
    if (autoRefreshEnabled.value) {
      try {
        await Promise.all([
          loadHealth(),
          loadTables()
        ])
        console.log('Auto-refreshed database data')
      } catch (error) {
        console.error('Auto-refresh failed:', error)
      }
    }
  }, 30000) // 30 seconds
}

const stopAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

const clearQuery = () => {
  queryText.value = ''
  queryResult.value = null
  queryError.value = null
}

const clearTable = async () => {
  if (!selectedTableName.value) return
  
  clearingTable.value = true
  
  try {
    await $fetch('/api/database/clear-table', {
      method: 'POST',
      body: { 
        tableName: selectedTableName.value,
        confirmText: clearTableConfirmText.value
      }
    })
    
    showClearTableModal.value = false
    clearTableConfirmText.value = ''
    selectedTableName.value = null
    await loadTables()
    await loadHealth()
  } catch (error) {
    console.error('Error clearing table:', error)
  } finally {
    clearingTable.value = false
  }
}

const clearDatabase = async () => {
  clearingDatabase.value = true
  
  try {
    await $fetch('/api/database/clear-database', {
      method: 'POST',
      body: {
        confirmText: clearDatabaseConfirmText.value
      }
    })
    
    showClearDatabaseModal.value = false
    clearDatabaseConfirmText.value = ''
    await loadTables()
    await loadHealth()
  } catch (error) {
    console.error('Error clearing database:', error)
  } finally {
    clearingDatabase.value = false
  }
}

const confirmClearTable = (tableName, rowCount) => {
  selectedTableName.value = tableName
  clearTableConfirmText.value = ''
  showClearTableModal.value = true
}

const confirmClearDatabase = () => {
  clearDatabaseConfirmText.value = ''
  showClearDatabaseModal.value = true
}

const handleClearTableEnter = () => {
  if (clearTableConfirmText.value === 'CLEAR') {
    clearTable()
  }
}

const handleClearDatabaseEnter = () => {
  if (clearDatabaseConfirmText.value === 'WIPE_DATABASE') {
    clearDatabase()
  }
}

const viewTableStructure = async (tableName) => {
  selectedStructureTable.value = tableName
  showStructureModal.value = true
  await loadTableStructure()
}

const loadTableStructure = async () => {
  if (!selectedStructureTable.value) return
  
  loadingStructure.value = true
  tableStructure.value = null
  
  try {
    const response = await $fetch(`/api/database/table-structure?table=${selectedStructureTable.value}`)
    tableStructure.value = response
  } catch (error) {
    console.error('Error loading table structure:', error)
    tableStructure.value = null
  } finally {
    loadingStructure.value = false
  }
}

// Lifecycle
onMounted(async () => {
  console.log('Database page mounted, loading data...')
  try {
    await Promise.all([
      loadHealth(),
      loadTables()
    ])
    console.log('Initial data loaded successfully')
  } catch (error) {
    console.error('Error loading initial data:', error)
  }
  startAutoRefresh()
})

// Cleanup on unmount
onUnmounted(() => {
  stopAutoRefresh()
})
</script>
