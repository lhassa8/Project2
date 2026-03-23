/**
 * Tests for the API hook — verifies request contracts, auth headers,
 * approval flow, and error handling.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ── Mock fetch globally ─────────────────────────────────────────────────────

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// ── Helpers ─────────────────────────────────────────────────────────────────

function jsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  })
}

beforeEach(() => {
  mockFetch.mockReset()
  localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ── Tests ───────────────────────────────────────────────────────────────────

describe('authFetch headers', () => {
  it('includes Content-Type by default', async () => {
    mockFetch.mockReturnValue(jsonResponse({ runs: [], total: 0 }))
    // Dynamic import to get fresh module
    const { createRun } = await import('../hooks/useApi')
    await createRun({
      agent_definition: { name: 'A', goal: 'G', tools: [], model: 'm', max_tokens: 100, temperature: 0 },
      run_context: { user_persona: 'u', initial_state: {} },
    })
    const [, opts] = mockFetch.mock.calls[0]
    expect(opts.headers['Content-Type']).toBe('application/json')
  })

  it('includes X-API-Key when set in localStorage', async () => {
    localStorage.setItem('agent_sandbox_api_key', 'ask_test123')
    mockFetch.mockReturnValue(jsonResponse({ id: 'run1', status: 'running' }))
    const { createRun } = await import('../hooks/useApi')
    await createRun({
      agent_definition: { name: 'A', goal: 'G', tools: [], model: 'm', max_tokens: 100, temperature: 0 },
      run_context: { user_persona: 'u', initial_state: {} },
    })
    const [, opts] = mockFetch.mock.calls[0]
    expect(opts.headers['X-API-Key']).toBe('ask_test123')
  })

  it('omits X-API-Key when not in localStorage', async () => {
    mockFetch.mockReturnValue(jsonResponse({ id: 'run1', status: 'running' }))
    const { createRun } = await import('../hooks/useApi')
    await createRun({
      agent_definition: { name: 'A', goal: 'G', tools: [], model: 'm', max_tokens: 100, temperature: 0 },
      run_context: { user_persona: 'u', initial_state: {} },
    })
    const [, opts] = mockFetch.mock.calls[0]
    expect(opts.headers['X-API-Key']).toBeUndefined()
  })
})

describe('createRun', () => {
  it('sends POST to /api/runs with correct body', async () => {
    mockFetch.mockReturnValue(jsonResponse({ id: 'run_abc', status: 'running' }))
    const { createRun } = await import('../hooks/useApi')
    const result = await createRun({
      agent_definition: { name: 'Test Agent', goal: 'Do stuff', tools: [{ name: 'read_file', enabled: true }], model: 'claude-sonnet-4-20250514', max_tokens: 4096, temperature: 0 },
      run_context: { user_persona: 'Tester', initial_state: { key: 'val' }, environment: { filesystem: { 'a.txt': 'hello' }, database: {}, http_stubs: [] } },
    })
    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/runs')
    expect(opts.method).toBe('POST')
    const body = JSON.parse(opts.body)
    expect(body.agent_definition.name).toBe('Test Agent')
    expect(body.run_context.environment.filesystem['a.txt']).toBe('hello')
    expect(result.id).toBe('run_abc')
  })
})

describe('submitApproval', () => {
  it('sends POST to /api/runs/{id}/approve', async () => {
    mockFetch.mockReturnValue(jsonResponse({ decision: 'approved', signature: 'sig123' }))
    const { submitApproval } = await import('../hooks/useApi')
    const result = await submitApproval('run_123', 'approved', 'Looks good')
    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/runs/run_123/approve')
    expect(opts.method).toBe('POST')
    const body = JSON.parse(opts.body)
    expect(body.decision).toBe('approved')
    expect(body.reviewer_notes).toBe('Looks good')
    expect(result.decision).toBe('approved')
  })

  it('handles rejection', async () => {
    mockFetch.mockReturnValue(jsonResponse({ decision: 'rejected', signature: 'sig456' }))
    const { submitApproval } = await import('../hooks/useApi')
    const result = await submitApproval('run_123', 'rejected', 'Too risky')
    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.decision).toBe('rejected')
    expect(result.decision).toBe('rejected')
  })

  it('handles changes_requested', async () => {
    mockFetch.mockReturnValue(jsonResponse({ decision: 'changes_requested', signature: '' }))
    const { submitApproval } = await import('../hooks/useApi')
    await submitApproval('run_123', 'changes_requested', 'Fix the SQL query')
    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.decision).toBe('changes_requested')
  })
})

describe('exportRun', () => {
  it('sends GET to /api/runs/{id}/export', async () => {
    mockFetch.mockReturnValue(jsonResponse({ export_version: '2.0', run: {}, risk_report: {} }))
    const { exportRun } = await import('../hooks/useApi')
    const result = await exportRun('run_123')
    expect(mockFetch.mock.calls[0][0]).toBe('/api/runs/run_123/export')
    expect(result.export_version).toBe('2.0')
  })
})

describe('compareRuns', () => {
  it('sends POST to /api/runs/compare', async () => {
    mockFetch.mockReturnValue(jsonResponse({ run_a_id: 'a', run_b_id: 'b', summary: [] }))
    const { compareRuns } = await import('../hooks/useApi')
    await compareRuns('run_a', 'run_b')
    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/runs/compare')
    const body = JSON.parse(opts.body)
    expect(body.run_id_a).toBe('run_a')
    expect(body.run_id_b).toBe('run_b')
  })
})

describe('replayRun', () => {
  it('sends POST with sandbox target by default', async () => {
    mockFetch.mockReturnValue(jsonResponse({ id: 'new_run', status: 'running' }))
    const { replayRun } = await import('../hooks/useApi')
    await replayRun('run_123')
    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.target).toBe('sandbox')
  })

  it('sends environment overrides', async () => {
    mockFetch.mockReturnValue(jsonResponse({ id: 'new_run', status: 'running' }))
    const { replayRun } = await import('../hooks/useApi')
    await replayRun('run_123', 'sandbox', { filesystem: { 'new.txt': 'data' } })
    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.environment_overrides.filesystem['new.txt']).toBe('data')
  })

  it('sends live target', async () => {
    mockFetch.mockReturnValue(jsonResponse({ status: 'queued' }))
    const { replayRun } = await import('../hooks/useApi')
    await replayRun('run_123', 'live')
    const body = JSON.parse(mockFetch.mock.calls[0][1].body)
    expect(body.target).toBe('live')
  })
})

describe('workspace API', () => {
  it('createApiKey sends correct request', async () => {
    mockFetch.mockReturnValue(jsonResponse({ key: 'ask_new', name: 'My Key', role: 'reviewer' }))
    const { createApiKey } = await import('../hooks/useApi')
    const result = await createApiKey('My Key', 'reviewer')
    const [url, opts] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/workspaces/api-keys')
    expect(opts.method).toBe('POST')
    const body = JSON.parse(opts.body)
    expect(body.name).toBe('My Key')
    expect(body.role).toBe('reviewer')
  })
})
