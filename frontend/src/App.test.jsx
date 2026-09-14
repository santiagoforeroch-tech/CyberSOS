import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

import App from './App.jsx'

vi.mock('./api/client.js', () => ({
  apiRequest: vi.fn((path) => Promise.resolve(path.includes('statistics')
    ? { total: 0, by_status: {} }
    : { items: [] })),
}))

describe('App', () => {
    afterEach(() => { cleanup(); window.location.hash = '' })

  it('muestra el título del proyecto', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: /Hay problemas por ahí\.? Actúa a tiempo\./i })).toBeInTheDocument()
  })

  it('muestra la bandeja administrativa', async () => {
    window.location.hash = '#/admin'
    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Hola, Administrador' })).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Caso, persona o categoría')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Filtrar por prioridad' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Actualizar' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Evolución de reportes' })).toBeInTheDocument()
  })

  it('explica las categorías del formulario en lenguaje sencillo', async () => {
    window.location.hash = '#/reportar'
    render(<App />)

    expect(await screen.findByText('Mensajes o páginas falsas que se hacen pasar por un banco, empresa o persona para pedir datos.')).toBeInTheDocument()
    expect(screen.getByText(/No necesitas conocer los términos técnicos/)).toBeInTheDocument()
  })
})
