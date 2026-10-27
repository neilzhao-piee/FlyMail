// 把 Vue SFC 里的中文 UI 文案包成 $t()/t()，并输出待翻译 key 清单。
import fs from 'fs'
import path from 'path'
import { parse } from '@vue/compiler-sfc'
import { parse as babelParse } from '@babel/parser'

const CJK = /[\u4e00-\u9fff]/
const root = 'src'
const files = []
function walkDir(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name)
    if (e.isDirectory()) walkDir(p)
    else if (e.name.endsWith('.vue')) files.push(p)
  }
}
walkDir(root)

const norm = (s) => s.trim().replace(/\s+/g, ' ')
const looksHtml = (s) => /<[a-zA-Z/!]/.test(s) || /style\s*=/.test(s) || /href\s*=/.test(s)
const allKeys = new Map() // key -> Set(files)

function addKey(k, f) {
  if (!k) return
  if (!allKeys.has(k)) allKeys.set(k, new Set())
  allKeys.get(k).add(f)
}

const skipAttrs = new Set(['class', 'style'])

for (const file of files) {
  const src = fs.readFileSync(file, 'utf8')
  const { descriptor } = parse(src, { filename: file })
  const edits = []

  // ---------- 模板 ----------
  const ast = descriptor.template?.ast
  if (ast) {
    const visit = (n) => {
      if (!n) return
      if (n.type === 2) { // TEXT
        const raw = n.content
        const key = norm(raw)
        if (key && CJK.test(key) && !looksHtml(key)) {
          addKey(key, file)
          edits.push({ start: n.loc.start.offset, end: n.loc.end.offset, text: `{{ $t(${JSON.stringify(key)}) }}` })
        }
      } else if (n.type === 1) { // ELEMENT
        for (const p of n.props || []) {
          if (p.type !== 6 || !p.value) continue // 仅静态属性
          const name = p.name
          if (skipAttrs.has(name) || name.startsWith('v-')) continue
          const val = p.value.content
          const key = norm(val)
          if (key && CJK.test(key) && !looksHtml(key)) {
            addKey(key, file)
            const js = JSON.stringify(key)
            const text = key.includes("'")
              ? `:${name}="$t(${js})"`
              : `:${name}='$t(${js})'`
            edits.push({ start: p.loc.start.offset, end: p.loc.end.offset, text })
          }
        }
      }
      for (const c of n.children || []) visit(c)
      if (n.branches) for (const b of n.branches) visit(b)
    }
    visit(ast)
  }

  // ---------- 脚本 ----------
  const sf = descriptor.scriptSetup || descriptor.script
  let needsT = false
  if (sf) {
    const offset = sf.loc.start.offset
    const code = sf.content
    let ast2
    try {
      ast2 = babelParse(code, { sourceType: 'module', plugins: ['typescript'], errorRecovery: true })
    } catch (e) { ast2 = null }
    if (ast2) {
      const visit2 = (node, parent) => {
        if (!node || typeof node !== 'object') return
        if (node.type === 'StringLiteral') {
          if (parent && parent.type === 'ImportDeclaration') return
          if (parent && parent.type === 'ObjectProperty' && parent.key === node) return
          const key = norm(node.value)
          if (key && CJK.test(key) && !looksHtml(key) && !(parent && parent.type === 'CallExpression' && parent.callee?.type === 'MemberExpression' && parent.callee.object?.name === 'console')) {
            addKey(key, file)
            needsT = true
            edits.push({ start: offset + node.start, end: offset + node.end, text: `t(${JSON.stringify(key)})` })
          }
          return
        }
        if (node.type === 'TemplateLiteral' && node.quasis?.some(q => CJK.test(q.value.cooked || q.value.raw))) {
          // 仅处理简单插值（无嵌套模板字符串）
          if (node.expressions.every(e => e.type !== 'TemplateLiteral')) {
            let key = ''
            node.quasis.forEach((q, i) => {
              key += q.value.cooked || q.value.raw
              if (i < node.expressions.length) key += `{${i}}`
            })
            key = norm(key)
            if (looksHtml(key)) return
            const exprSrc = node.expressions.map(e => code.slice(e.start, e.end)).join(', ')
            addKey(key, file)
            needsT = true
            edits.push({ start: offset + node.start, end: offset + node.end, text: `t(${JSON.stringify(key)}, [${exprSrc}])` })
          }
          return
        }
        for (const k of Object.keys(node)) {
          const v = node[k]
          if (Array.isArray(v)) v.forEach(x => visit2(x, node))
          else if (v && typeof v === 'object' && typeof v.type === 'string') visit2(v, node)
        }
      }
      visit2(ast2, null)
    }
  }

  if (edits.length === 0) continue

  // 注入 useI18n
  if (needsT && sf) {
    const s = sf.content
    const parts = []
    if (!/from 'vue-i18n'/.test(s)) parts.push("import { useI18n } from 'vue-i18n'")
    if (!/const \{ t \} = useI18n\(\)/.test(s)) parts.push("const { t } = useI18n()")
    if (parts.length) {
      edits.push({ start: sf.loc.start.offset, end: sf.loc.start.offset, text: "\n" + parts.join('\n') })
    }
  }
  edits.sort((a, b) => b.start - a.start)
  let out = src
  for (const e of edits) out = out.slice(0, e.start) + e.text + out.slice(e.end)
  fs.writeFileSync(file, out)
  console.log(`wrapped ${file} (${edits.length} edits)`)
}

const keys = [...allKeys.keys()].sort()
fs.writeFileSync('/root/i18n/keys.txt', keys.join('\n'))
console.log('unique keys:', keys.length)
