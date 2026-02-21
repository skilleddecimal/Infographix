import { Link } from 'react-router-dom'
import { Layout } from '../components/layout'
import { Card, Button, Badge } from '../components/ui'

const plans = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'Perfect for trying out Infographix',
    features: [
      '10 generations per month',
      'Basic templates',
      '2 variations per generation',
      'PowerPoint export',
      'Community support',
    ],
    cta: 'Get Started',
    ctaVariant: 'outline' as const,
    href: '/register',
  },
  {
    name: 'Pro',
    price: '$29',
    period: 'per month',
    description: 'For professionals who create regularly',
    features: [
      '200 generations per month',
      'All templates',
      '10 variations per generation',
      'All export formats (PPTX, PDF, PNG, SVG)',
      'Priority email support',
      'Custom brand colors',
      'No watermarks',
    ],
    cta: 'Start Pro Trial',
    ctaVariant: 'primary' as const,
    href: '/register?plan=pro',
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: 'per year',
    description: 'For teams with advanced needs',
    features: [
      'Unlimited generations',
      'All templates + custom templates',
      'Unlimited variations',
      'All export formats + API access',
      'Dedicated support',
      'Brand guidelines enforcement',
      'Team collaboration',
      'SSO & advanced security',
      'SLA guarantee',
    ],
    cta: 'Contact Sales',
    ctaVariant: 'outline' as const,
    href: '/contact',
  },
]

const faqs = [
  {
    question: 'What counts as a generation?',
    answer:
      'Each time you generate an infographic from a prompt, it counts as one generation. Creating variations of an existing generation also counts.',
  },
  {
    question: 'Can I upgrade or downgrade my plan?',
    answer:
      'Yes, you can change your plan at any time. When upgrading, you will be charged the prorated difference. When downgrading, the change takes effect at the next billing cycle.',
  },
  {
    question: 'Do unused generations roll over?',
    answer:
      'No, generation credits reset at the start of each billing cycle. We recommend the Pro plan if you need consistent access to more generations.',
  },
  {
    question: 'What payment methods do you accept?',
    answer:
      'We accept all major credit cards (Visa, MasterCard, American Express) and PayPal. Enterprise customers can also pay via invoice.',
  },
  {
    question: 'Is there a free trial for Pro?',
    answer:
      'Yes, we offer a 14-day free trial of Pro. No credit card required to start your trial.',
  },
  {
    question: 'Can I cancel anytime?',
    answer:
      'Yes, you can cancel your subscription at any time. Your access continues until the end of your current billing period.',
  },
]

export function Pricing() {
  return (
    <Layout>
      {/* Header */}
      <section className="py-16 bg-gradient-to-b from-primary-50 to-white">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Simple, transparent pricing
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Choose the plan that fits your needs. All plans include access to our AI
            infographic generator.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-16">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {plans.map((plan) => (
              <Card
                key={plan.name}
                padding="lg"
                className={`relative ${
                  plan.popular
                    ? 'border-2 border-primary-500 shadow-glow'
                    : ''
                }`}
              >
                {plan.popular && (
                  <Badge
                    variant="primary"
                    className="absolute -top-3 left-1/2 -translate-x-1/2"
                  >
                    Most Popular
                  </Badge>
                )}

                <div className="text-center mb-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-2">
                    {plan.name}
                  </h3>
                  <div className="flex items-baseline justify-center gap-1">
                    <span className="text-4xl font-bold text-gray-900">
                      {plan.price}
                    </span>
                    <span className="text-gray-500">/{plan.period}</span>
                  </div>
                  <p className="text-gray-600 mt-2">{plan.description}</p>
                </div>

                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <svg
                        className="w-5 h-5 text-primary-600 flex-shrink-0 mt-0.5"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <span className="text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>

                <Link to={plan.href} className="block">
                  <Button
                    variant={plan.ctaVariant}
                    size="lg"
                    className="w-full"
                  >
                    {plan.cta}
                  </Button>
                </Link>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-16 bg-gray-50">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">
            Frequently asked questions
          </h2>
          <div className="max-w-3xl mx-auto">
            <div className="space-y-6">
              {faqs.map((faq) => (
                <Card key={faq.question} padding="md">
                  <h3 className="font-semibold text-gray-900 mb-2">
                    {faq.question}
                  </h3>
                  <p className="text-gray-600">{faq.answer}</p>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Still have questions?
          </h2>
          <p className="text-gray-600 mb-6">
            We're here to help. Contact our team for personalized assistance.
          </p>
          <Link to="/contact">
            <Button variant="outline">Contact Us</Button>
          </Link>
        </div>
      </section>
    </Layout>
  )
}
