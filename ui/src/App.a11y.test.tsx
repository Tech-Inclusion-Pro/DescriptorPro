// Automated accessibility checks (axe) over the shell, every pane, and the
// display settings widget. Automated checks do not replace the manual
// keyboard + VoiceOver pass (docs/a11y-checklist.md).

import { render, fireEvent, screen } from '@testing-library/react'
import { axe } from 'jest-axe'
import App from './App'

// jsdom lacks these; the components only need them to exist.
beforeAll(() => {
  window.HTMLElement.prototype.setPointerCapture = () => {}
  window.fetch = (() => Promise.reject(new Error('no network in tests'))) as typeof fetch
})

async function expectNoViolations(container: HTMLElement) {
  const results = await axe(container)
  expect(results.violations).toEqual([])
}

test('shell and media pane have no axe violations', async () => {
  const { container } = render(<App />)
  await expectNoViolations(container)
})

test('every step pane has no axe violations', async () => {
  const { container } = render(<App />)
  for (const name of ['Say what you want', 'Need check', 'Review', 'Export']) {
    fireEvent.click(screen.getByRole('tab', { name: new RegExp(name, 'i') }))
    await expectNoViolations(container)
  }
})

test('live and standards views have no axe violations', async () => {
  const { container } = render(<App />)
  fireEvent.click(screen.getByRole('button', { name: /live session/i }))
  await expectNoViolations(container)
  fireEvent.click(screen.getByRole('button', { name: /description standards/i }))
  await expectNoViolations(container)
})

test('display settings panel opens and has no axe violations', async () => {
  const { container } = render(<App />)
  fireEvent.click(screen.getByRole('button', { name: /display settings/i }))
  expect(screen.getByRole('group', { name: /display settings/i })).toBeTruthy()
  await expectNoViolations(container)
})

test('step tabs follow the tablist keyboard pattern', () => {
  render(<App />)
  const tabs = screen.getAllByRole('tab')
  expect(tabs).toHaveLength(5)
  expect(tabs[0].getAttribute('aria-selected')).toBe('true')
  fireEvent.keyDown(tabs[0], { key: 'ArrowRight' })
  expect(tabs[1].getAttribute('aria-selected')).toBe('true')
  fireEvent.keyDown(tabs[1], { key: 'End' })
  expect(tabs[4].getAttribute('aria-selected')).toBe('true')
  fireEvent.keyDown(tabs[4], { key: 'Home' })
  expect(tabs[0].getAttribute('aria-selected')).toBe('true')
})
