"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { 
  AlertCircle, CheckCircle, XCircle, RefreshCw, 
  Activity, Terminal, Wrench, Eye
} from "lucide-react"
import errorLogger from '@/lib/error-logger'

interface Diagnostic {
  summary: {
    total_logs: number
    total_errors: number
    unique_error_patterns: number
    services_tracked: number
    unhealthy_services: number
  }
  unhealthy_services: any[]
  top_errors: any[]
  recent_errors: any[]
  recommendations: any[]
}

interface FixSuggestion {
  issue: string
  priority: string
  action: string
  command: string
  automated: boolean
}

export function SystemDiagnostics() {
  const [diagnostics, setDiagnostics] = useState<Diagnostic | null>(null)
  const [fixes, setFixes] = useState<FixSuggestion[]>([])
  const [isVisible, setIsVisible] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [autoFixing, setAutoFixing] = useState(false)

  const fetchDiagnostics = async () => {
    setIsLoading(true)
    try {
      const diag = await errorLogger.getDiagnostics()
      const fixSuggestions = await errorLogger.getFixSuggestions()
      
      if (diag) setDiagnostics(diag)
      if (fixSuggestions) setFixes(fixSuggestions.fixes || [])
      
      // Auto-show if there are critical issues
      if (diag && (diag.summary.unhealthy_services > 0 || diag.summary.total_errors > 10)) {
        setIsVisible(true)
      }
    } catch (error) {
      console.error('Failed to fetch diagnostics:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchDiagnostics()
    const interval = setInterval(fetchDiagnostics, 30000) // Update every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const executeFix = async (command: string) => {
    setAutoFixing(true)
    try {
      // Send command to backend to execute
      const response = await fetch('http://localhost:9000/api/execute-fix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command })
      })
      
      if (response.ok) {
        errorLogger.info('Fix executed successfully', { command })
        setTimeout(fetchDiagnostics, 2000) // Refresh after fix
      } else {
        errorLogger.error('Fix execution failed', { command })
      }
    } catch (error) {
      errorLogger.error('Failed to execute fix', { command, error })
    } finally {
      setAutoFixing(false)
    }
  }

  if (!diagnostics) return null

  const hasIssues = diagnostics.summary.unhealthy_services > 0 || diagnostics.summary.total_errors > 0

  return (
    <>
      {/* Floating diagnostic button */}
      <div className="fixed bottom-4 right-4 z-50">
        <Button
          variant={hasIssues ? "destructive" : "outline"}
          size="icon"
          onClick={() => setIsVisible(!isVisible)}
          className="rounded-full shadow-lg"
        >
          {hasIssues ? (
            <AlertCircle className="h-4 w-4 animate-pulse" />
          ) : (
            <Activity className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Diagnostic Panel */}
      {isVisible && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40" onClick={() => setIsVisible(false)}>
          <div 
            className="fixed right-0 top-0 h-full w-full max-w-2xl bg-background border-l shadow-xl overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6 space-y-6">
              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold">System Diagnostics</h2>
                  <p className="text-sm text-muted-foreground">
                    Real-time system health and error tracking
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={fetchDiagnostics}
                    disabled={isLoading}
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => window.open('http://localhost:9013/dashboard', '_blank')}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Full Dashboard
                  </Button>
                </div>
              </div>

              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Logs</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{diagnostics.summary.total_logs}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Errors</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-red-500">
                      {diagnostics.summary.total_errors}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Services</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {diagnostics.summary.services_tracked}
                      {diagnostics.summary.unhealthy_services > 0 && (
                        <span className="text-sm text-red-500 ml-2">
                          ({diagnostics.summary.unhealthy_services} unhealthy)
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Recommendations */}
              {diagnostics.recommendations.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Wrench className="h-4 w-4" />
                      Recommended Actions
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {diagnostics.recommendations.map((rec, i) => (
                      <Alert key={i} variant={rec.priority === 'HIGH' ? 'destructive' : 'default'}>
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>{rec.issue}</AlertTitle>
                        <AlertDescription>
                          <p>{rec.action}</p>
                          {rec.command && (
                            <div className="mt-2">
                              <code className="text-xs bg-muted px-2 py-1 rounded">
                                {rec.command}
                              </code>
                              <Button
                                size="sm"
                                variant="outline"
                                className="ml-2"
                                onClick={() => executeFix(rec.command)}
                                disabled={autoFixing}
                              >
                                Execute Fix
                              </Button>
                            </div>
                          )}
                        </AlertDescription>
                      </Alert>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* Auto-Fix Suggestions */}
              {fixes.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Auto-Fix Available</CardTitle>
                    <CardDescription>
                      {fixes.filter(f => f.automated).length} issues can be fixed automatically
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {fixes.filter(f => f.automated).map((fix, i) => (
                        <div key={i} className="flex items-center justify-between p-2 border rounded">
                          <div>
                            <Badge variant={fix.priority === 'HIGH' ? 'destructive' : 'default'}>
                              {fix.priority}
                            </Badge>
                            <span className="ml-2 text-sm">{fix.issue}</span>
                          </div>
                          <Button
                            size="sm"
                            onClick={() => executeFix(fix.command)}
                            disabled={autoFixing}
                          >
                            Fix
                          </Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Recent Errors */}
              {diagnostics.recent_errors.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Recent Errors</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {diagnostics.recent_errors.slice(0, 5).map((error, i) => (
                        <div key={i} className="text-xs p-2 bg-red-500/10 border border-red-500/20 rounded">
                          <div className="text-red-500 font-mono">
                            [{error.timestamp}] {error.source}
                          </div>
                          <div className="text-red-400 mt-1">{error.message}</div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Top Error Patterns */}
              {diagnostics.top_errors.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Top Error Patterns</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {diagnostics.top_errors.map((error, i) => (
                        <div key={i} className="flex items-center justify-between">
                          <div>
                            <Badge variant="outline">{error.category}</Badge>
                            <span className="ml-2 text-sm">{error.solution}</span>
                          </div>
                          <Badge variant="secondary">{error.count}x</Badge>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}