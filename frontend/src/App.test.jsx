import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

import App from './App.jsx'

vi.mock('./api/client.js', () => ({
  apiRequest: vi.fn((path) => Promise.resolve(path.includes('/agent/chat')
    ? { conversation_id: null, message: 'Respuesta del asistente: dime cuándo ocurrió.', draft: { category: null, summary: '', facts: [], missing_information: [], evidence_requested: [], needs_human_review: true }, ready_to_confirm: false }
    : path.includes('statistics') ? { total: 0, by_status: {} } : { items: [] })),
}))

describe('App', () => {
    afterEach(() => { cleanup(); window.location.hash = '' })

  it('muestra el título del proyecto', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: /Hay problemas por ahí\.? Actúa a tiempo\./i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Cómo funciona' })).toHaveAttribute('href', '/#como-funciona')
  })

  it('muestra la bandeja administrativa', async () => {
    window.location.hash = '#/admin'
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Centro de control' })).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Buscar casos, usuarios, recursos…')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Evolución de reportes' })).toBeInTheDocument()
  })

  it('muestra el asistente ciudadano y permite enviar un mensaje', async () => {
    window.location.hash = '#/reportar'
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Cuéntame qué ocurrió' })).toBeInTheDocument()
    const input = screen.getByLabelText('Escribe tu mensaje')
    fireEvent.change(input, { target: { value: 'Me llegó un enlace falso' } })
    fireEvent.submit(input.closest('form'))
    expect(await screen.findByText(/No compartas contraseñas|cuándo ocurrió|qué pasó/i)).toBeInTheDocument()
  })
})
