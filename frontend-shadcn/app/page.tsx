"use client"

import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { 
  BarChart3, Bitcoin, TrendingUp, Zap, Shield, Target,
  Clock, DollarSign, Activity, ArrowRight, Flame
} from "lucide-react"

export default function HomePage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b backdrop-blur">
        <div className="container mx-auto px-4 py-6">
          <div className="text-center">
            <h1 className="text-4xl font-bold mb-2">Alpaca Trading System</h1>
            <p className="text-lg text-muted-foreground">Choose Your Trading Mode</p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 max-w-6xl mx-auto">
          
          {/* Stock Trading Card */}
          <Card className="relative overflow-hidden hover:shadow-lg transition-shadow cursor-pointer" 
                onClick={() => router.push('/stocks')}>
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-green-500/20 to-transparent rounded-bl-full" />
            <CardHeader>
              <div className="flex items-center justify-between mb-4">
                <BarChart3 className="h-12 w-12 text-green-500" />
                <Badge className="bg-green-500">Market Hours</Badge>
              </div>
              <CardTitle className="text-2xl">Stock Trading Bot</CardTitle>
              <CardDescription>Traditional equity markets with regulated hours</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">9:30 AM - 4:00 PM ET</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">10-30 trades/hour</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Share quantities</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Target className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">0.1-0.3% targets</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">T+2 settlement</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Activity className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Day orders only</span>
                  </div>
                </div>
              </div>
              
              <div className="pt-4">
                <Button className="w-full" size="lg">
                  Open Stock Trading
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
              
              <div className="text-xs text-muted-foreground text-center">
                Trades AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, SPY, QQQ
              </div>
            </CardContent>
          </Card>

          {/* Crypto Trading Card */}
          <Card className="relative overflow-hidden hover:shadow-lg transition-shadow cursor-pointer" 
                onClick={() => router.push('/crypto')}>
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-orange-500/20 to-transparent rounded-bl-full" />
            <CardHeader>
              <div className="flex items-center justify-between mb-4">
                <Bitcoin className="h-12 w-12 text-orange-500" />
                <Badge className="bg-orange-500">24/7 Trading</Badge>
              </div>
              <CardTitle className="text-2xl">Crypto Trading Bot</CardTitle>
              <CardDescription>Cryptocurrency markets never close</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">24/7 availability</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Zap className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">15-40 trades/hour</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Fractional trading</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Target className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">0.1-0.5% targets</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">T+0 instant</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Activity className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">GTC orders</span>
                  </div>
                </div>
              </div>
              
              <div className="pt-4">
                <Button className="w-full" size="lg" variant="secondary">
                  Open Crypto Trading
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
              
              <div className="text-xs text-muted-foreground text-center">
                Trades BTC, ETH, LTC, BCH, UNI, LINK, AAVE, MKR, SOL, AVAX
              </div>
            </CardContent>
          </Card>

          {/* Scalping Card */}
          <Card className="relative overflow-hidden hover:shadow-lg transition-shadow cursor-pointer border-2 border-red-500/20" 
                onClick={() => router.push('/scalping')}>
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-red-500/20 to-transparent rounded-bl-full" />
            <CardHeader>
              <div className="flex items-center justify-between mb-4">
                <Flame className="h-12 w-12 text-red-500" />
                <Badge className="bg-red-500 animate-pulse">EXTREME</Badge>
              </div>
              <CardTitle className="text-2xl">Scalping Mode</CardTitle>
              <CardDescription>Ultra high-frequency crypto scalping</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">30s-3m holds</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Zap className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">40-100 trades/hour</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Micro positions</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Target className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">0.1-0.5% targets</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Tight stops</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Activity className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">Hotkey trading</span>
                  </div>
                </div>
              </div>
              
              <div className="pt-4">
                <Button className="w-full bg-red-500 hover:bg-red-600" size="lg">
                  Enter Scalping Mode
                  <Flame className="ml-2 h-4 w-4" />
                </Button>
              </div>
              
              <div className="text-xs text-muted-foreground text-center">
                ⚠️ High-risk, high-reward trading strategy
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Features Section */}
        <div className="mt-12 max-w-4xl mx-auto">
          <Card>
            <CardHeader className="text-center">
              <CardTitle>High-Frequency Scalping Strategy</CardTitle>
              <CardDescription>Both bots use advanced technical indicators for rapid trading</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4">
                  <div className="rounded-full bg-primary/10 w-12 h-12 flex items-center justify-center mx-auto mb-2">
                    <TrendingUp className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-1">Fast EMA Crossovers</h3>
                  <p className="text-sm text-muted-foreground">3/8 period EMAs for quick signals</p>
                </div>
                <div className="text-center p-4">
                  <div className="rounded-full bg-primary/10 w-12 h-12 flex items-center justify-center mx-auto mb-2">
                    <Activity className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-1">Volume Analysis</h3>
                  <p className="text-sm text-muted-foreground">20%+ volume spikes detection</p>
                </div>
                <div className="text-center p-4">
                  <div className="rounded-full bg-primary/10 w-12 h-12 flex items-center justify-center mx-auto mb-2">
                    <Zap className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-1">StochRSI Signals</h3>
                  <p className="text-sm text-muted-foreground">Momentum-based entry/exit</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}