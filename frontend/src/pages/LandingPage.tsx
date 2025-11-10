import { FileJson, Zap, Shield, Globe, ArrowRight, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

const API_DOCS_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/docs`;

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileJson className="h-8 w-8 text-blue-600" />
            <span className="text-xl font-bold text-slate-900">AI Document Processor</span>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            <a href="#features" className="text-slate-600 hover:text-slate-900 transition-colors">Features</a>
            <a href="#pricing" className="text-slate-600 hover:text-slate-900 transition-colors">Pricing</a>
            <a href={API_DOCS_URL} target="_blank" rel="noopener noreferrer" className="text-slate-600 hover:text-slate-900 transition-colors">API Docs</a>
            <Button variant="ghost" onClick={() => navigate('/login')}>Log In</Button>
            <Button onClick={() => navigate('/signup')}>Sign Up</Button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 md:py-32">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 text-blue-700 text-sm font-medium mb-8">
            <Zap className="h-4 w-4" />
            Powered by Vision Language Models
          </div>

          <h1 className="text-5xl md:text-6xl font-bold text-slate-900 mb-6 leading-tight">
            Transform Documents into
            <span className="text-blue-600"> Structured Data</span>
          </h1>

          <p className="text-xl text-slate-600 mb-12 leading-relaxed">
            Extract invoices, receipts, forms, and any document into clean JSON schemas.
            Powered by AI, designed for developers.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <Button size="lg" className="text-lg px-8 py-6" onClick={() => navigate('/schema-builder')}>
              Try Schema Builder
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button size="lg" variant="outline" className="text-lg px-8 py-6" onClick={() => window.open(API_DOCS_URL, '_blank')}>
              View API Docs
            </Button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 max-w-2xl mx-auto pt-8 border-t">
            <div>
              <div className="text-3xl font-bold text-slate-900">99.9%</div>
              <div className="text-sm text-slate-600">Accuracy</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-slate-900">&lt;2s</div>
              <div className="text-sm text-slate-600">Processing Time</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-slate-900">50+</div>
              <div className="text-sm text-slate-600">Document Types</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="bg-slate-50 py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-slate-900 mb-4">
              Everything you need to process documents
            </h2>
            <p className="text-xl text-slate-600">
              Enterprise-grade features for modern applications
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {/* Feature 1 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
              <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center mb-6">
                <FileJson className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">Custom JSON Schemas</h3>
              <p className="text-slate-600 mb-4">
                Define your own extraction schemas or use our pre-built templates for invoices, receipts, and forms.
              </p>
              <ul className="space-y-2">
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Visual schema builder
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Template library
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  JSON Schema validation
                </li>
              </ul>
            </div>

            {/* Feature 2 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
              <div className="h-12 w-12 bg-purple-100 rounded-lg flex items-center justify-center mb-6">
                <Zap className="h-6 w-6 text-purple-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">Multi-Model AI</h3>
              <p className="text-slate-600 mb-4">
                Choose from multiple VLLM providers for optimal accuracy and cost. Switch providers seamlessly.
              </p>
              <ul className="space-y-2">
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Google Gemini 2.5 Flash
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  GPT-4 Vision
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  DeepSeek & more
                </li>
              </ul>
            </div>

            {/* Feature 3 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
              <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center mb-6">
                <Shield className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">Enterprise Security</h3>
              <p className="text-slate-600 mb-4">
                Multi-tenant architecture with row-level security. Your data is isolated and encrypted.
              </p>
              <ul className="space-y-2">
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  JWT authentication
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  RBAC permissions
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Tenant isolation
                </li>
              </ul>
            </div>

            {/* Feature 4 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
              <div className="h-12 w-12 bg-orange-100 rounded-lg flex items-center justify-center mb-6">
                <Globe className="h-6 w-6 text-orange-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">RESTful API</h3>
              <p className="text-slate-600 mb-4">
                Simple, well-documented REST API. Integrate in minutes with any language or framework.
              </p>
              <ul className="space-y-2">
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  OpenAPI/Swagger docs
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Webhook support
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Batch processing
                </li>
              </ul>
            </div>

            {/* Feature 5 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
              <div className="h-12 w-12 bg-pink-100 rounded-lg flex items-center justify-center mb-6">
                <FileJson className="h-6 w-6 text-pink-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">Flexible Output</h3>
              <p className="text-slate-600 mb-4">
                Get extracted data in JSON, CSV, or XML. Perfect for databases, spreadsheets, or analytics.
              </p>
              <ul className="space-y-2">
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  JSON export
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  CSV conversion
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Custom formatting
                </li>
              </ul>
            </div>

            {/* Feature 6 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
              <div className="h-12 w-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-6">
                <Zap className="h-6 w-6 text-indigo-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">Real-time Processing</h3>
              <p className="text-slate-600 mb-4">
                Upload and process documents instantly. Track job status in real-time with webhooks.
              </p>
              <ul className="space-y-2">
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Async job queue
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Status webhooks
                </li>
                <li className="flex items-center gap-2 text-sm text-slate-600">
                  <Check className="h-4 w-4 text-green-600" />
                  Retry logic
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-slate-900 mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-xl text-slate-600">
              Pay only for what you use. No hidden fees.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Free Tier */}
            <div className="bg-white p-8 rounded-2xl border-2 border-slate-200">
              <h3 className="text-2xl font-bold text-slate-900 mb-2">Starter</h3>
              <p className="text-slate-600 mb-6">Perfect for trying out</p>
              <div className="mb-6">
                <span className="text-4xl font-bold text-slate-900">$0</span>
                <span className="text-slate-600">/month</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center gap-2 text-slate-600">
                  <Check className="h-5 w-5 text-green-600" />
                  100 documents/month
                </li>
                <li className="flex items-center gap-2 text-slate-600">
                  <Check className="h-5 w-5 text-green-600" />
                  Basic templates
                </li>
                <li className="flex items-center gap-2 text-slate-600">
                  <Check className="h-5 w-5 text-green-600" />
                  Email support
                </li>
              </ul>
              <Button variant="outline" className="w-full" onClick={() => navigate('/signup')}>
                Get Started
              </Button>
            </div>

            {/* Pro Tier */}
            <div className="bg-blue-600 p-8 rounded-2xl border-2 border-blue-600 shadow-lg scale-105 relative">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-yellow-400 text-slate-900 px-4 py-1 rounded-full text-sm font-semibold">
                Popular
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">Professional</h3>
              <p className="text-blue-100 mb-6">For growing businesses</p>
              <div className="mb-6">
                <span className="text-4xl font-bold text-white">$99</span>
                <span className="text-blue-100">/month</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center gap-2 text-white">
                  <Check className="h-5 w-5 text-blue-200" />
                  10,000 documents/month
                </li>
                <li className="flex items-center gap-2 text-white">
                  <Check className="h-5 w-5 text-blue-200" />
                  All templates
                </li>
                <li className="flex items-center gap-2 text-white">
                  <Check className="h-5 w-5 text-blue-200" />
                  Custom schemas
                </li>
                <li className="flex items-center gap-2 text-white">
                  <Check className="h-5 w-5 text-blue-200" />
                  Priority support
                </li>
                <li className="flex items-center gap-2 text-white">
                  <Check className="h-5 w-5 text-blue-200" />
                  API access
                </li>
              </ul>
              <Button className="w-full bg-white text-blue-600 hover:bg-blue-50" onClick={() => navigate('/signup')}>
                Start Free Trial
              </Button>
            </div>

            {/* Enterprise Tier */}
            <div className="bg-white p-8 rounded-2xl border-2 border-slate-200">
              <h3 className="text-2xl font-bold text-slate-900 mb-2">Enterprise</h3>
              <p className="text-slate-600 mb-6">For large organizations</p>
              <div className="mb-6">
                <span className="text-4xl font-bold text-slate-900">Custom</span>
              </div>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center gap-2 text-slate-600">
                  <Check className="h-5 w-5 text-green-600" />
                  Unlimited documents
                </li>
                <li className="flex items-center gap-2 text-slate-600">
                  <Check className="h-5 w-5 text-green-600" />
                  Dedicated support
                </li>
                <li className="flex items-center gap-2 text-slate-600">
                  <Check className="h-5 w-5 text-green-600" />
                  SLA guarantee
                </li>
                <li className="flex items-center gap-2 text-slate-600">
                  <Check className="h-5 w-5 text-green-600" />
                  On-premise option
                </li>
                <li className="flex items-center gap-2 text-slate-600">
                  <Check className="h-5 w-5 text-green-600" />
                  Custom integrations
                </li>
              </ul>
              <Button variant="outline" className="w-full" onClick={() => window.location.href = 'mailto:sales@example.com'}>
                Contact Sales
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-blue-600 py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold text-white mb-4">
            Ready to transform your documents?
          </h2>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Join thousands of developers using our API to extract structured data from documents.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="bg-white text-blue-600 hover:bg-blue-50 text-lg px-8 py-6" onClick={() => navigate('/signup')}>
              Start Free Trial
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button size="lg" variant="outline" className="border-white text-white hover:bg-blue-700 text-lg px-8 py-6" onClick={() => window.open(API_DOCS_URL, '_blank')}>
              View Documentation
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <FileJson className="h-6 w-6 text-blue-400" />
                <span className="text-white font-semibold">AI Document Processor</span>
              </div>
              <p className="text-sm">
                Transform documents into structured data with AI-powered extraction.
              </p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href={API_DOCS_URL} className="hover:text-white transition-colors">API Docs</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition-colors">About</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition-colors">Privacy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Security</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-8 text-sm text-center">
            © 2025 AI Document Processor. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
