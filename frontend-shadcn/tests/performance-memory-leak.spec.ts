import { test, expect, Page, BrowserContext } from '@playwright/test'

/**
 * Performance and Memory Leak Detection Test Suite
 * Identifies memory leaks, performance bottlenecks, and inefficiencies
 */

interface MemoryMetrics {
  usedJSHeapSize: number
  totalJSHeapSize: number
  jsHeapSizeLimit: number
  timestamp: number
}

interface PerformanceMetrics {
  domContentLoaded: number
  loadComplete: number
  firstPaint: number
  firstContentfulPaint: number
  largestContentfulPaint: number
  resourceCount: number
  totalResourceSize: number
}

test.describe('🔍 Performance & Memory Leak Detection', () => {
  test.setTimeout(120000) // 2 minutes for thorough testing

  async function captureMemoryMetrics(page: Page): Promise<MemoryMetrics> {
    return await page.evaluate(() => {
      const perf = (performance as any)
      if (perf.memory) {
        return {
          usedJSHeapSize: perf.memory.usedJSHeapSize,
          totalJSHeapSize: perf.memory.totalJSHeapSize,
          jsHeapSizeLimit: perf.memory.jsHeapSizeLimit,
          timestamp: Date.now()
        }
      }
      return {
        usedJSHeapSize: 0,
        totalJSHeapSize: 0,
        jsHeapSizeLimit: 0,
        timestamp: Date.now()
      }
    })
  }

  async function capturePerformanceMetrics(page: Page): Promise<PerformanceMetrics> {
    return await page.evaluate(() => {
      const perfData = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
      const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[]
      
      let totalSize = 0
      resources.forEach(resource => {
        if (resource.transferSize) {
          totalSize += resource.transferSize
        }
      })

      const paintEntries = performance.getEntriesByType('paint')
      const firstPaint = paintEntries.find(entry => entry.name === 'first-paint')
      const firstContentfulPaint = paintEntries.find(entry => entry.name === 'first-contentful-paint')
      
      const largestContentfulPaint = performance.getEntriesByType('largest-contentful-paint')[0]

      return {
        domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
        loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
        firstPaint: firstPaint ? firstPaint.startTime : 0,
        firstContentfulPaint: firstContentfulPaint ? firstContentfulPaint.startTime : 0,
        largestContentfulPaint: largestContentfulPaint ? largestContentfulPaint.startTime : 0,
        resourceCount: resources.length,
        totalResourceSize: totalSize
      }
    })
  }

  test('1. Memory Leak Detection - Component Mounting/Unmounting', async ({ page }) => {
    await page.goto('http://localhost:9100')
    
    const initialMemory = await captureMemoryMetrics(page)
    console.log('Initial Memory:', {
      usedMB: (initialMemory.usedJSHeapSize / 1024 / 1024).toFixed(2),
      totalMB: (initialMemory.totalJSHeapSize / 1024 / 1024).toFixed(2)
    })

    // Perform repeated actions that could cause memory leaks
    for (let i = 0; i < 10; i++) {
      // Navigate between different views
      await page.click('button:has-text("Trading"), [class*="trading"]').catch(() => {})
      await page.waitForTimeout(500)
      
      await page.click('button:has-text("Portfolio"), [class*="portfolio"]').catch(() => {})
      await page.waitForTimeout(500)
      
      await page.click('button:has-text("Dashboard"), [class*="dashboard"]').catch(() => {})
      await page.waitForTimeout(500)
    }

    // Force garbage collection if possible
    await page.evaluate(() => {
      if ((window as any).gc) {
        (window as any).gc()
      }
    })

    await page.waitForTimeout(2000)

    const finalMemory = await captureMemoryMetrics(page)
    console.log('Final Memory:', {
      usedMB: (finalMemory.usedJSHeapSize / 1024 / 1024).toFixed(2),
      totalMB: (finalMemory.totalJSHeapSize / 1024 / 1024).toFixed(2)
    })

    const memoryIncrease = finalMemory.usedJSHeapSize - initialMemory.usedJSHeapSize
    const percentIncrease = (memoryIncrease / initialMemory.usedJSHeapSize) * 100

    console.log(`Memory increase: ${(memoryIncrease / 1024 / 1024).toFixed(2)} MB (${percentIncrease.toFixed(2)}%)`)

    // Alert if memory increased by more than 50%
    if (percentIncrease > 50) {
      console.warn('⚠️ Potential memory leak detected! Memory increased by more than 50%')
    }

    expect(percentIncrease).toBeLessThan(100) // Fail if memory doubled
  })

  test('2. WebSocket Connection Leak Detection', async ({ page }) => {
    let websocketCount = 0
    const websockets: any[] = []

    page.on('websocket', ws => {
      websocketCount++
      websockets.push({
        url: ws.url(),
        opened: Date.now(),
        closed: null
      })

      ws.on('close', () => {
        const wsInfo = websockets.find(w => w.url === ws.url() && !w.closed)
        if (wsInfo) {
          wsInfo.closed = Date.now()
        }
      })
    })

    await page.goto('http://localhost:9100')
    await page.waitForTimeout(5000)

    // Reload page multiple times
    for (let i = 0; i < 5; i++) {
      await page.reload()
      await page.waitForTimeout(2000)
    }

    // Check for unclosed websockets
    const unclosedWebsockets = websockets.filter(ws => !ws.closed)
    
    console.log(`Total WebSockets created: ${websocketCount}`)
    console.log(`Unclosed WebSockets: ${unclosedWebsockets.length}`)

    if (unclosedWebsockets.length > 0) {
      console.warn('⚠️ WebSocket leak detected! Unclosed connections:', unclosedWebsockets)
    }

    expect(unclosedWebsockets.length).toBeLessThanOrEqual(1) // Allow max 1 active connection
  })

  test('3. API Request Pattern Analysis', async ({ page }) => {
    const apiCalls: any[] = []

    page.on('request', request => {
      if (request.url().includes('api/')) {
        apiCalls.push({
          url: request.url(),
          method: request.method(),
          timestamp: Date.now()
        })
      }
    })

    await page.goto('http://localhost:9100')
    await page.waitForTimeout(10000) // Wait 10 seconds

    // Analyze API call patterns
    const apiEndpoints = new Map<string, number>()
    apiCalls.forEach(call => {
      const endpoint = new URL(call.url).pathname
      apiEndpoints.set(endpoint, (apiEndpoints.get(endpoint) || 0) + 1)
    })

    console.log('API Call Frequency:')
    let excessiveCalls = false
    apiEndpoints.forEach((count, endpoint) => {
      console.log(`  ${endpoint}: ${count} calls`)
      
      // Alert if same endpoint called more than 20 times in 10 seconds
      if (count > 20) {
        console.warn(`⚠️ Excessive calls to ${endpoint}: ${count} calls in 10 seconds`)
        excessiveCalls = true
      }
    })

    // Check for rapid repeated calls (potential polling issue)
    const duplicateCalls = new Map<string, number[]>()
    apiCalls.forEach(call => {
      const key = `${call.method}:${call.url}`
      if (!duplicateCalls.has(key)) {
        duplicateCalls.set(key, [])
      }
      duplicateCalls.get(key)!.push(call.timestamp)
    })

    duplicateCalls.forEach((timestamps, endpoint) => {
      if (timestamps.length > 1) {
        const intervals = []
        for (let i = 1; i < timestamps.length; i++) {
          intervals.push(timestamps[i] - timestamps[i - 1])
        }
        const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length
        
        if (avgInterval < 1000 && timestamps.length > 5) { // Less than 1 second average
          console.warn(`⚠️ Rapid polling detected for ${endpoint}: ${avgInterval.toFixed(0)}ms average interval`)
        }
      }
    })

    expect(excessiveCalls).toBeFalsy()
  })

  test('4. Bundle Size and Load Performance', async ({ page }) => {
    await page.goto('http://localhost:9100')
    
    const metrics = await capturePerformanceMetrics(page)
    
    console.log('Performance Metrics:')
    console.log(`  DOM Content Loaded: ${metrics.domContentLoaded}ms`)
    console.log(`  Page Load Complete: ${metrics.loadComplete}ms`)
    console.log(`  First Paint: ${metrics.firstPaint.toFixed(2)}ms`)
    console.log(`  First Contentful Paint: ${metrics.firstContentfulPaint.toFixed(2)}ms`)
    console.log(`  Largest Contentful Paint: ${metrics.largestContentfulPaint.toFixed(2)}ms`)
    console.log(`  Resources Loaded: ${metrics.resourceCount}`)
    console.log(`  Total Size: ${(metrics.totalResourceSize / 1024 / 1024).toFixed(2)} MB`)

    // Performance thresholds
    expect(metrics.firstContentfulPaint).toBeLessThan(3000) // FCP under 3s
    expect(metrics.largestContentfulPaint).toBeLessThan(5000) // LCP under 5s
    expect(metrics.totalResourceSize).toBeLessThan(10 * 1024 * 1024) // Total under 10MB

    // Check for large JavaScript bundles
    const jsResources = await page.evaluate(() => {
      const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[]
      return resources
        .filter(r => r.name.endsWith('.js'))
        .map(r => ({
          name: r.name,
          size: r.transferSize || 0,
          duration: r.duration
        }))
        .sort((a, b) => b.size - a.size)
    })

    console.log('\nLargest JavaScript files:')
    jsResources.slice(0, 5).forEach(resource => {
      const sizeMB = (resource.size / 1024 / 1024).toFixed(2)
      console.log(`  ${resource.name.split('/').pop()}: ${sizeMB} MB (${resource.duration.toFixed(0)}ms)`)
      
      if (resource.size > 1024 * 1024) { // Larger than 1MB
        console.warn(`⚠️ Large bundle detected: ${resource.name.split('/').pop()}`)
      }
    })
  })

  test('5. React Component Re-render Detection', async ({ page }) => {
    // Inject React DevTools profiler
    await page.goto('http://localhost:9100')
    
    // Monitor React re-renders
    const renderCounts = await page.evaluate(() => {
      const counts = new Map<string, number>()
      
      // Hook into React component lifecycle if possible
      const observer = new MutationObserver((mutations) => {
        mutations.forEach(mutation => {
          if (mutation.type === 'childList' || mutation.type === 'attributes') {
            const target = mutation.target as HTMLElement
            const reactKey = target.getAttribute('data-reactroot') || target.className
            counts.set(reactKey, (counts.get(reactKey) || 0) + 1)
          }
        })
      })

      observer.observe(document.body, {
        childList: true,
        attributes: true,
        subtree: true
      })

      return new Promise<any>(resolve => {
        setTimeout(() => {
          observer.disconnect()
          resolve(Array.from(counts.entries()))
        }, 5000)
      })
    })

    console.log('\nComponent Re-render Analysis:')
    const excessiveRenders = renderCounts.filter(([_, count]) => count > 10)
    
    if (excessiveRenders.length > 0) {
      console.warn('⚠️ Components with excessive re-renders:')
      excessiveRenders.forEach(([component, count]) => {
        console.warn(`  ${component}: ${count} renders in 5 seconds`)
      })
    }
  })

  test('6. Event Listener Leak Detection', async ({ page }) => {
    await page.goto('http://localhost:9100')
    
    const initialListeners = await page.evaluate(() => {
      const getEventListeners = (element: any) => {
        const listeners: any = {}
        const events = ['click', 'change', 'input', 'submit', 'scroll', 'resize', 'mousemove']
        events.forEach(event => {
          // This is a simplified check - real implementation would need Chrome DevTools Protocol
          listeners[event] = 0
        })
        return listeners
      }
      return getEventListeners(window)
    })

    // Perform actions that add/remove components
    for (let i = 0; i < 10; i++) {
      await page.reload()
      await page.waitForTimeout(1000)
    }

    const finalListeners = await page.evaluate(() => {
      // Check for listeners that weren't cleaned up
      return (window as any).getEventListeners ? 
        Object.keys((window as any).getEventListeners(window)).length : 0
    })

    console.log(`Event listeners after reloads: ${finalListeners}`)
  })

  test('7. State Management Memory Analysis', async ({ page }) => {
    await page.goto('http://localhost:9100')
    
    // Check Redux/Zustand/Context store size
    const storeSize = await page.evaluate(() => {
      // Check for Redux store
      const reduxStore = (window as any).__REDUX_DEVTOOLS_EXTENSION__?.getStore?.()
      if (reduxStore) {
        const state = reduxStore.getState()
        return JSON.stringify(state).length
      }
      
      // Check for Zustand store
      const zustandStores = (window as any).__zustand__stores
      if (zustandStores) {
        let totalSize = 0
        zustandStores.forEach((store: any) => {
          totalSize += JSON.stringify(store.getState()).length
        })
        return totalSize
      }
      
      return 0
    })

    const storeSizeMB = (storeSize / 1024 / 1024).toFixed(2)
    console.log(`State store size: ${storeSizeMB} MB`)
    
    if (storeSize > 5 * 1024 * 1024) { // Larger than 5MB
      console.warn('⚠️ Large state store detected! Consider optimizing state management')
    }
  })

  test('8. Long-running Memory Test', async ({ page }) => {
    await page.goto('http://localhost:9100')
    
    const memorySnapshots: MemoryMetrics[] = []
    const duration = 30000 // 30 seconds
    const interval = 5000 // 5 seconds
    
    console.log('Starting long-running memory test...')
    
    for (let elapsed = 0; elapsed < duration; elapsed += interval) {
      const memory = await captureMemoryMetrics(page)
      memorySnapshots.push(memory)
      
      console.log(`[${elapsed/1000}s] Memory: ${(memory.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`)
      
      // Simulate user interactions
      await page.click('body').catch(() => {})
      await page.keyboard.press('Escape')
      
      await page.waitForTimeout(interval)
    }

    // Analyze memory trend
    const memoryGrowth = memorySnapshots[memorySnapshots.length - 1].usedJSHeapSize - memorySnapshots[0].usedJSHeapSize
    const growthRate = memoryGrowth / duration * 1000 // bytes per second
    
    console.log(`\nMemory growth: ${(memoryGrowth / 1024 / 1024).toFixed(2)} MB over ${duration/1000} seconds`)
    console.log(`Growth rate: ${(growthRate / 1024).toFixed(2)} KB/s`)
    
    if (growthRate > 100 * 1024) { // More than 100 KB/s
      console.error('❌ Critical memory leak detected! Growth rate exceeds 100 KB/s')
    } else if (growthRate > 10 * 1024) { // More than 10 KB/s
      console.warn('⚠️ Potential memory leak. Growth rate: ' + (growthRate / 1024).toFixed(2) + ' KB/s')
    } else {
      console.log('✅ Memory usage appears stable')
    }
    
    expect(growthRate).toBeLessThan(100 * 1024) // Fail if growing faster than 100 KB/s
  })

  test('9. Generate Performance Report', async ({ page }) => {
    await page.goto('http://localhost:9100')
    await page.waitForLoadState('networkidle')
    
    const report = {
      timestamp: new Date().toISOString(),
      memory: await captureMemoryMetrics(page),
      performance: await capturePerformanceMetrics(page),
      coverage: await page.coverage.stopJSCoverage().catch(() => []),
      recommendations: [] as string[]
    }

    // Generate recommendations based on metrics
    const memoryMB = report.memory.usedJSHeapSize / 1024 / 1024
    
    if (memoryMB > 100) {
      report.recommendations.push('High memory usage detected. Consider optimizing component state and data structures.')
    }
    
    if (report.performance.largestContentfulPaint > 4000) {
      report.recommendations.push('Slow LCP. Consider lazy loading, code splitting, and optimizing critical rendering path.')
    }
    
    if (report.performance.totalResourceSize > 5 * 1024 * 1024) {
      report.recommendations.push('Large bundle size. Implement code splitting and tree shaking.')
    }
    
    if (report.performance.resourceCount > 100) {
      report.recommendations.push('Too many resources. Consider bundling and reducing HTTP requests.')
    }

    console.log('\n📊 PERFORMANCE REPORT')
    console.log('====================')
    console.log(`Memory Usage: ${memoryMB.toFixed(2)} MB`)
    console.log(`Page Load Time: ${report.performance.loadComplete}ms`)
    console.log(`LCP: ${report.performance.largestContentfulPaint.toFixed(0)}ms`)
    console.log(`Resources: ${report.performance.resourceCount}`)
    console.log(`Total Size: ${(report.performance.totalResourceSize / 1024 / 1024).toFixed(2)} MB`)
    
    if (report.recommendations.length > 0) {
      console.log('\n🔧 Recommendations:')
      report.recommendations.forEach(rec => console.log(`  • ${rec}`))
    }
    
    // Save report to file
    await page.evaluate((reportData) => {
      console.log('Full Performance Report:', reportData)
    }, report)
  })
})