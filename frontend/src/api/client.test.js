import { describe, expect, it } from 'vitest'

import { errorMessage } from './client.js'

describe('errorMessage', () => {
  it('convierte errores de validación de FastAPI en texto legible', () => {
    expect(errorMessage({ detail: [{ loc: ['body', 'email'], msg: 'value is not a valid email address' }] }))
      .toBe('Revisa el campo email: value is not a valid email address')
  })

  it('conserva un mensaje textual del servidor', () => {
    expect(errorMessage({ detail: 'El correo no está autorizado' })).toBe('El correo no está autorizado')
  })
})
