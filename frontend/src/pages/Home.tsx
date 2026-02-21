import { Link } from 'react-router-dom'
import { Layout } from '../components/layout'
import { Button, Card } from '../components/ui'

const features = [
  {
    title: 'AI-Powered Generation',
    description:
      'Describe what you want in plain English. Our AI understands context and creates professional infographics.',
    icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  },
  {
    title: 'Professional Templates',
    description:
      'Choose from dozens of professionally designed templates: funnels, timelines, pyramids, and more.',
    icon: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z',
  },
  {
    title: 'Creative Variations',
    description:
      'Get multiple design variations with one click. Choose the style that fits your brand best.',
    icon: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z',
  },
  {
    title: 'Export Anywhere',
    description:
      'Download as editable PowerPoint, SVG, PNG, or PDF. Perfect for presentations and reports.',
    icon: 'M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
  },
]

const testimonials = [
  {
    quote:
      "Infographix saves me hours every week. I used to spend half a day on each slide deck, now it's done in minutes.",
    author: 'Sarah Chen',
    role: 'Marketing Director',
    company: 'TechCorp',
  },
  {
    quote:
      'The quality of the generated infographics is incredible. My clients think I hired a professional designer.',
    author: 'Michael Rodriguez',
    role: 'Consultant',
    company: 'Strategy Partners',
  },
  {
    quote:
      'Finally, a tool that understands what business infographics should look like. Clean, professional, and on-brand.',
    author: 'Emily Watson',
    role: 'Product Manager',
    company: 'StartupXYZ',
  },
]

export function Home() {
  return (
    <Layout>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary-50 to-white py-20 sm:py-32">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-6">
              Create Beautiful Infographics
              <span className="text-primary-600"> with AI</span>
            </h1>
            <p className="text-xl text-gray-600 mb-8">
              Transform your ideas into professional PowerPoint infographics in seconds.
              Just describe what you want, and let our AI do the rest.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register">
                <Button size="lg">
                  Start Free
                  <svg
                    className="w-5 h-5 ml-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7l5 5m0 0l-5 5m5-5H6"
                    />
                  </svg>
                </Button>
              </Link>
              <Link to="/templates">
                <Button variant="outline" size="lg">
                  Browse Templates
                </Button>
              </Link>
            </div>
            <p className="text-sm text-gray-500 mt-4">
              10 free generations per month. No credit card required.
            </p>
          </div>
        </div>

        {/* Decorative gradient */}
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-200 rounded-full blur-3xl opacity-30" />
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-primary-300 rounded-full blur-3xl opacity-20" />
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Everything you need for professional infographics
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              From idea to presentation-ready slide in seconds, not hours.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature) => (
              <Card key={feature.title} padding="lg" className="text-center">
                <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-6 h-6 text-primary-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d={feature.icon}
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600">{feature.description}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Loved by professionals
            </h2>
            <p className="text-lg text-gray-600">
              See what our users are saying about Infographix.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial) => (
              <Card key={testimonial.author} padding="lg">
                <blockquote className="text-gray-700 mb-4">
                  "{testimonial.quote}"
                </blockquote>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-primary-700">
                      {testimonial.author[0]}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{testimonial.author}</p>
                    <p className="text-sm text-gray-500">
                      {testimonial.role}, {testimonial.company}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary-600">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Ready to create amazing infographics?
          </h2>
          <p className="text-xl text-primary-100 mb-8 max-w-2xl mx-auto">
            Join thousands of professionals who save hours every week with Infographix.
          </p>
          <Link to="/register">
            <Button
              size="lg"
              className="bg-white text-primary-600 hover:bg-primary-50"
            >
              Get Started Free
            </Button>
          </Link>
        </div>
      </section>
    </Layout>
  )
}
