import { render, screen } from "@testing-library/react"
import { test, vi } from "vitest"

import { WhatsAppPanel } from "./WhatsAppPanel"


vi.mock("./whatsappApi", () => ({
  whatsappApi: {
    connection: vi.fn().mockResolvedValue({ state: "disconnected" }),
    conversations: vi.fn().mockResolvedValue([]),
  },
}))


test("muestra el estado desconectado", async () => {
  render(<WhatsAppPanel />)
  expect(await screen.findByText("disconnected")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Conectar" })).toBeInTheDocument()
})
