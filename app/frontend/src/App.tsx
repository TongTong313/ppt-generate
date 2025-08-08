import React, { useCallback, useMemo, useRef, useState } from 'react'

type RethinkRound = {
  round: number
  think: string
  answer: string
  modify: string
}

const BACKEND_HTTP = (import.meta as any).env?.VITE_BACKEND_URL || 'http://localhost:8000'
const BACKEND_WS = BACKEND_HTTP.replace('http', 'ws')

function sanitizeTags(s: string): string {
  if (!s) return ''
  // 兼容性更强的标签清洗：优先移除我们定义的结构化标记，再兜底清理其他尖括号包裹内容
  const tags = [
    'outline', 'page', 'page_num', 'title', 'summary', 'body', 'img_table_advice',
    'advice', 'rethinking_think', 'rethinking_answer', 'modify_answer',
  ]
  let out = s
  for (const t of tags) {
    const reOpen = new RegExp(`<${t}>`, 'g')
    const reClose = new RegExp(`</${t}>`, 'g')
    out = out.replace(reOpen, '').replace(reClose, '')
  }
  // 清理形如 <xxx ...> 或 </xxx> 或 <xxx/> 的其他未知标签
  out = out.replace(/<\/?[a-zA-Z0-9_:-]+(?:\s+[^>]*)?>/g, '')
  return out
}

function pickBetween(s: string, tag: string): string {
  const m = new RegExp(`<${tag}>([\\s\\S]*?)<\/${tag}>`).exec(s)
  return m?.[1]?.trim() || ''
}

type PageCard = {
  pageNum: string
  title: string
  summary: string
  body: string
  advice: string
  raw: string
}

export default function App() {
  const [query, setQuery] = useState('请为“企业私有化大模型平台建设方案”生成一个结构完整、逻辑严密且内容详尽的PPT，约12-20页')
  const [referenceText, setReferenceText] = useState('')
  const [uploaded, setUploaded] = useState<{ path: string; filename: string } | null>(null)
  const [rethink, setRethink] = useState(true)
  const [maxRounds, setMaxRounds] = useState(3)

  const [connecting, setConnecting] = useState(false)
  const [outlineThink, setOutlineThink] = useState('')
  const [outlineAnswer, setOutlineAnswer] = useState('')
  const [outlineForConfirm, setOutlineForConfirm] = useState('')
  const [contentStarted, setContentStarted] = useState(false)
  const [contentThink, setContentThink] = useState('')
  const [contentAnswer, setContentAnswer] = useState('')
  const [rethinks, setRethinks] = useState<RethinkRound[]>([])
  const [pages, setPages] = useState<string[]>([])
  const [pageCards, setPageCards] = useState<PageCard[]>([])
  const [expandedPages, setExpandedPages] = useState<Record<number, boolean>>({})
  const [modifyBuffer, setModifyBuffer] = useState('')
  const [modifyRound, setModifyRound] = useState<number | null>(null)
  const [creationPrimed, setCreationPrimed] = useState(false)

  // 折叠管理（结束自动折叠，可点击展开）
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({
    outline_think_col: false,
    outline_answer_col: true,
    content_think_col: true,
    rethinks_col: true,
    preview_col: false,
  })
  const wsRef = useRef<WebSocket | null>(null)

  const resetAll = () => {
    setOutlineThink('')
    setOutlineAnswer('')
    setContentThink('')
    setContentAnswer('')
    setRethinks([])
    setPages([])
    setPageCards([])
    setExpandedPages({})
    setCollapsed({ outline_think_col: false, outline_answer_col: true, content_think_col: true, rethinks_col: true, preview_col: false })
    setModifyBuffer('')
    setModifyRound(null)
    setCreationPrimed(false)
  }

  const handleUpload = async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BACKEND_HTTP}/upload`, { method: 'POST', body: form })
    const data = await res.json()
    if (data.success) {
      setUploaded({ path: data.path, filename: data.filename })
      // 自动抽取
      const ext = new FormData()
      ext.append('path', data.path)
      const er = await fetch(`${BACKEND_HTTP}/extract`, { method: 'POST', body: ext })
      const ed = await er.json()
      if (ed.success) setReferenceText(ed.text)
    }
  }

  const ensureConnection = useCallback(async () => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return
    }
    setConnecting(true)
    const ws = new WebSocket(`${BACKEND_WS}/ws/generate`)
    wsRef.current = ws
    ws.onopen = () => setConnecting(false)
    ws.onmessage = (ev) => {
      const evt = JSON.parse(ev.data)
      const stage = evt.stage as string
      const type = evt.type as string | undefined

      if (stage === 'reference_loaded') {
        // ignore but could notify
        return
      }

      if (stage === 'outline_think') {
        if (type === 'start') {
          setOutlineThink('')
          setCollapsed((c) => ({ ...c, outline_think_col: false }))
        } else if (type === 'token') {
          setOutlineThink((s) => sanitizeTags(s + (evt.text || '')))
        } else if (type === 'end') {
          setCollapsed((c) => ({ ...c, outline_think_col: true }))
        }
      } else if (stage === 'outline_answer') {
        if (type === 'start') {
          setOutlineAnswer('')
          setCollapsed((c) => ({ ...c, outline_answer_col: false }))
        } else if (type === 'token') {
          setOutlineAnswer((s) => sanitizeTags(s + (evt.text || '')))
        } else if (type === 'end') {
          setCollapsed((c) => ({ ...c, outline_answer_col: true }))
        }
      } else if (stage === 'outline_done') {
        // 服务端发送纯 <outline> 提取的文本，供用户修改确认
        setOutlineForConfirm(evt.outline || '')
      } else if (stage === 'content_think') {
        if (type === 'start') {
          setContentThink('')
          setCollapsed((c) => ({ ...c, content_think_col: false }))
        } else if (type === 'token') {
          setContentThink((s) => sanitizeTags(s + (evt.text || '')))
        } else if (type === 'end') {
          setCollapsed((c) => ({ ...c, content_think_col: true }))
        }
      } else if (stage === 'content_answer') {
        if (type === 'start') {
          setContentAnswer('')
          setCollapsed((c) => ({ ...c, preview_col: false }))
        } else if (type === 'token') {
          // 累加原始文本并实时解析 <page> 块形成卡片
          setContentAnswer((prev) => {
            const next = prev + (evt.text || '')
            const re = /<page>([\s\S]*?)<\/page>/g
            const found: PageCard[] = []
            let m: RegExpExecArray | null
            while ((m = re.exec(next)) !== null) {
              const raw = m[1]
              const pageNum = pickBetween(raw, 'page_num')
              const title = pickBetween(raw, 'title')
              const summary = pickBetween(raw, 'summary')
              const body = pickBetween(raw, 'body')
              const advice = pickBetween(raw, 'img_table_advice')
              found.push({ pageNum, title, summary, body, advice, raw })
            }
            setPageCards((old) => {
              if (found.length > old.length) {
                return found
              }
              return old
            })
            return next
          })
        }
      } else if (stage === 'rethinking_think' || stage === 'rethinking_answer' || stage === 'modify_answer') {
        const round = evt.round as number
        setRethinks((arr) => {
          const next = [...arr]
          let r = next.find((x) => x.round === round)
          if (!r) {
            r = { round, think: '', answer: '', modify: '' }
            next.push(r)
            next.sort((a, b) => a.round - b.round)
          }
          if (type === 'token') {
            if (stage === 'rethinking_think') r.think = sanitizeTags((r.think || '') + (evt.text || ''))
            if (stage === 'rethinking_answer') r.answer = sanitizeTags((r.answer || '') + (evt.text || ''))
            if (stage === 'modify_answer') r.modify = sanitizeTags((r.modify || '') + (evt.text || ''))
          }
          return next
        })
        // 实时根据修改流重建卡片
        if (stage === 'modify_answer') {
          if (type === 'start') {
            setModifyBuffer('')
            setModifyRound(round)
          } else if (type === 'token') {
            setModifyBuffer((prev) => {
              const buf = prev + (evt.text || '')
              const re = /<page>([\s\S]*?)<\/page>/g
              const cards: PageCard[] = []
              let m: RegExpExecArray | null
              while ((m = re.exec(buf)) !== null) {
                const raw = m[1]
                const pageNum = sanitizeTags(pickBetween(raw, 'page_num'))
                const title = sanitizeTags(pickBetween(raw, 'title'))
                const summary = sanitizeTags(pickBetween(raw, 'summary'))
                const body = sanitizeTags(pickBetween(raw, 'body'))
                const advice = sanitizeTags(pickBetween(raw, 'img_table_advice'))
                cards.push({ pageNum, title, summary, body, advice, raw })
              }
              if (cards.length) setPageCards(cards)
              return buf
            })
          } else if (type === 'end') {
            // 一轮修改结束可折叠反思
            setCollapsed((c) => ({ ...c, rethinks_col: true }))
          }
        }
      } else if (stage === 'content_done') {
        const arr: string[] = evt.pages || []
        setPages(arr)
        // 最终同步一次卡片
        const cards: PageCard[] = arr.map((p) => ({
          pageNum: sanitizeTags(pickBetween(p, 'page_num')),
          title: sanitizeTags(pickBetween(p, 'title')),
          summary: sanitizeTags(pickBetween(p, 'summary')),
          body: sanitizeTags(pickBetween(p, 'body')),
          advice: sanitizeTags(pickBetween(p, 'img_table_advice')),
          raw: p,
        }))
        setPageCards(cards)
      } else if (stage === 'done') {
        const arr: string[] = evt.pages || []
        setPages(arr)
        ws.close()
        setConnecting(false)
        // 所有流程完成后，整体预览保持，其他面板保持折叠
      } else if (stage === 'error') {
        console.error('error:', evt.error)
        ws.close()
        setConnecting(false)
      }
    }
    ws.onclose = () => setConnecting(false)
  }, [])

  const startOutline = useCallback(async () => {
    resetAll()
    await ensureConnection()
    wsRef.current?.send(
      JSON.stringify({
        action: 'start_outline',
        query,
        reference_content: referenceText || undefined,
        reference_path: uploaded?.path || undefined,
      }),
    )
  }, [ensureConnection, query, referenceText, uploaded])

  const onCreationClick = useCallback(async () => {
    if (!creationPrimed) {
      setCreationPrimed(true)
      return
    }
    await startOutline()
  }, [creationPrimed, startOutline])

  const confirmOutlineAndStartContent = useCallback(async () => {
    if (!outlineForConfirm.trim()) return
    setContentStarted(true)
    await ensureConnection()
    wsRef.current?.send(
      JSON.stringify({
        action: 'start_content',
        outline: outlineForConfirm,
        rethink,
        max_rethink_times: maxRounds,
      }),
    )
  }, [ensureConnection, outlineForConfirm, rethink, maxRounds])

  const pageGrid = useMemo(() => {
    return pageCards.map((p, i) => {
      const isOpen = !!expandedPages[i]
      return (
        <div key={i} className="glass p-3 space-y-2">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs text-slate-400">{p.pageNum || `第 ${i + 1} 页`}</div>
              <div className="text-base font-semibold text-sky-300">{p.title || `第 ${i + 1} 页`}</div>
            </div>
            <button
              className="text-xs px-2 py-1 rounded glass"
              onClick={() => setExpandedPages((m) => ({ ...m, [i]: !isOpen }))}
            >
              {isOpen ? '收起' : '详情'}
            </button>
          </div>
          {p.summary && (
            <div className="text-slate-200 text-sm whitespace-pre-wrap">{p.summary}</div>
          )}
          {isOpen && (
            <div className="space-y-2">
              {p.body && (
                <div>
                  <div className="text-slate-400 text-xs mb-1">正文</div>
                  <pre className="mono whitespace-pre-wrap text-slate-300/90 text-xs max-h-40 overflow-auto">{p.body}</pre>
                </div>
              )}
              {p.advice && (
                <div>
                  <div className="text-slate-400 text-xs mb-1">图像/表格建议</div>
                  <ul className="list-disc pl-5 text-slate-300/90 text-xs space-y-1 max-h-32 overflow-auto">
                    {formatAdviceToList(p.advice).map((it, idx) => (
                      <li key={idx}>{it}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )
    })
  }, [pageCards, expandedPages])

  function formatAdviceToList(text: string): string[] {
    const cleaned = sanitizeTags(text)
    const parts = cleaned
      .split(/\n+|；|;|。/)
      .map(s => s.trim())
      .filter(Boolean)
      .map(s => s.replace(/^(\d+[\.|\)]\s*|[-*]\s*)/, ''))
    return parts.length ? parts : [cleaned]
  }

  return (
    <div className="h-full flex flex-col">
      <header className="px-6 py-4 flex items-center justify-between">
        <div className="text-xl font-bold tracking-wider">
          <span className="text-sky-400">PPT</span> 智能体生成器
        </div>
        <div className="text-slate-400 text-sm">实时思考 · 流式渲染 · 多格式资料上传</div>
      </header>

      <main className="flex-1 px-6 pb-8 grid grid-cols-12 gap-4">
        {/* 左侧：用户输入区 */}
        <section className="col-span-4 space-y-4">
          <div className="glass p-4 space-y-3">
            <div className="text-slate-200">需求描述</div>
            <textarea
              className="w-full min-h-32 glass p-3 outline-none"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="请输入PPT需求..."
            />
            <div className="flex items-center gap-2">
              <label className="inline-flex items-center gap-2">
                <input type="checkbox" checked={rethink} onChange={(e) => setRethink(e.target.checked)} />
                <span>启用反思</span>
              </label>
              <input
                type="number"
                min={1}
                max={5}
                className="glass px-2 py-1 w-20"
                value={maxRounds}
                onChange={(e) => setMaxRounds(Number(e.target.value))}
              />
              <span className="text-slate-400 text-sm">最大轮数</span>
            </div>
            <div className="flex gap-2">
              <label className="glass px-3 py-2 cursor-pointer">
                <input
                  type="file"
                  className="hidden"
                  onChange={(e) => e.target.files && e.target.files[0] && handleUpload(e.target.files[0])}
                />
                上传参考材料
              </label>
              {uploaded && <div className="text-slate-400 text-sm truncate">{uploaded.filename}</div>}
            </div>
            <div className="space-y-2">
              <div className="text-slate-200">参考内容（可编辑）</div>
              <textarea
                className="w-full min-h-40 glass p-3 outline-none mono"
                placeholder="上传后自动抽取，也可自行粘贴"
                value={referenceText}
                onChange={(e) => setReferenceText(e.target.value)}
              />
            </div>
            <div className="flex gap-3 items-center">
              <button
                className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-600 disabled:opacity-50"
                onClick={onCreationClick}
                disabled={connecting}
              >
                PPT创作
              </button>
              {creationPrimed && <span className="text-xs text-slate-400">再次点击开始</span>}
              <button className="ml-auto px-4 py-2 rounded-lg glass" onClick={resetAll}>重置</button>
            </div>
          </div>
        </section>

        {/* 右侧：生成过程（上：智能体运行过程；下：PPT 内容预览） */}
        <section className="col-span-8 space-y-4">
          {/* 上：智能体运行过程 */}
          <div className="glass p-4 space-y-3">
            <div className="text-slate-200">智能体运行过程</div>

            {/* 大纲思考（到达再展示） */}
            {outlineThink && (
              <div className="glass">
                <div
                  className="px-3 py-2 flex items-center justify-between cursor-pointer"
                  onClick={() => setCollapsed((c) => ({ ...c, outline_think_col: !c.outline_think_col }))}
                >
                  <div className="text-sky-300 text-sm">大纲思考</div>
                  <div className="text-xs text-slate-400">{collapsed.outline_think_col ? '展开' : '收起'}</div>
                </div>
                {!collapsed.outline_think_col && (
                  <pre className="px-3 pb-3 mono whitespace-pre-wrap text-xs text-slate-300/90 max-h-40 overflow-auto">{outlineThink}</pre>
                )}
              </div>
            )}

            {/* 大纲草案（到达再展示） */}
            {outlineAnswer && (
              <div className="glass">
                <div
                  className="px-3 py-2 flex items-center justify-between cursor-pointer"
                  onClick={() => setCollapsed((c) => ({ ...c, outline_answer_col: !c.outline_answer_col }))}
                >
                  <div className="text-sky-300 text-sm">大纲草案</div>
                  <div className="text-xs text-slate-400">{collapsed.outline_answer_col ? '展开' : '收起'}</div>
                </div>
                {!collapsed.outline_answer_col && (
                  <pre className="px-3 pb-3 mono whitespace-pre-wrap text-xs text-slate-300/90 max-h-40 overflow-auto">{outlineAnswer}</pre>
                )}
              </div>
            )}

            {/* 大纲确认（到达再展示） */}
            {outlineForConfirm && !contentStarted && (
              <div className="space-y-2">
                <div className="text-slate-200">确认并可修改大纲</div>
                <textarea
                  className="w-full min-h-40 glass p-3 outline-none mono"
                  value={outlineForConfirm}
                  onChange={(e) => setOutlineForConfirm(e.target.value)}
                />
                <button
                  className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50"
                  onClick={confirmOutlineAndStartContent}
                >
                  确认大纲并继续生成页面
                </button>
              </div>
            )}

            {/* 页面思考（到达再展示） */}
            {contentThink && (
              <div className="glass">
                <div
                  className="px-3 py-2 flex items-center justify-between cursor-pointer"
                  onClick={() => setCollapsed((c) => ({ ...c, content_think_col: !c.content_think_col }))}
                >
                  <div className="text-emerald-300 text-sm">页面思考</div>
                  <div className="text-xs text-slate-400">{collapsed.content_think_col ? '展开' : '收起'}</div>
                </div>
                {!collapsed.content_think_col && (
                  <pre className="px-3 pb-3 mono whitespace-pre-wrap text-xs text-slate-300/90 max-h-40 overflow-auto">{contentThink}</pre>
                )}
              </div>
            )}

            {/* 反思过程（到达再展示） */}
            {rethinks.some((r) => r.think || r.answer || r.modify) && (
              <div className="glass">
                <div
                  className="px-3 py-2 flex items-center justify-between cursor-pointer"
                  onClick={() => setCollapsed((c) => ({ ...c, rethinks_col: !c.rethinks_col }))}
                >
                  <div className="text-fuchsia-300 text-sm">反思过程</div>
                  <div className="text-xs text-slate-400">{collapsed.rethinks_col ? '展开' : '收起'}</div>
                </div>
                {!collapsed.rethinks_col && (
                  <div className="px-3 pb-3 space-y-3">
                    {rethinks.map((r) => (
                      <div key={r.round} className="space-y-2">
                        {(r.think || r.answer || r.modify) && (
                          <div className="text-slate-400 text-xs">第 {r.round} 轮</div>
                        )}
                        {r.think && (
                          <div>
                            <div className="text-slate-300 text-sm mb-1">思考</div>
                            <pre className="mono whitespace-pre-wrap text-xs text-slate-300/90 max-h-32 overflow-auto">{r.think}</pre>
                          </div>
                        )}
                        {r.answer && (
                          <div>
                            <div className="text-slate-300 text-sm mb-1">建议</div>
                            <ul className="list-disc pl-5 text-slate-300/90 text-xs space-y-1 max-h-32 overflow-auto">
                              {formatAdviceToList(r.answer).map((it, idx) => (
                                <li key={idx}>{it}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {r.modify && (
                          <div>
                            <div className="text-slate-300 text-sm mb-1">修改</div>
                            <pre className="mono whitespace-pre-wrap text-xs text-slate-300/90 max-h-32 overflow-auto">{r.modify}</pre>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 下：PPT 内容预览 */}
          <div className="glass p-4 space-y-3">
            <div className="text-slate-200">PPT 内容预览</div>
            {pageCards.length > 0 && (
              <div className="grid grid-cols-2 gap-3">{pageGrid}</div>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}

