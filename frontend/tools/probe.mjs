import { parse } from '@vue/compiler-sfc'
import fs from 'fs'
const src = fs.readFileSync('src/views/About.vue','utf8')
const { descriptor } = parse(src, { filename: 'About.vue' })
const tpl = descriptor.template
console.log('tpl loc start', tpl.loc.start.offset, JSON.stringify(src.slice(tpl.loc.start.offset, tpl.loc.start.offset+30)))
const walk = (n, depth=0) => {
  if (!n) return
  if (n.type === 2) console.log('TEXT', JSON.stringify(n.content.slice(0,20)), n.loc.start.offset, n.loc.end.offset, JSON.stringify(src.slice(n.loc.start.offset, n.loc.end.offset).slice(0,30)))
  if (n.type === 1) for (const p of n.props||[]) { if (p.type===6 && p.value && /[\u4e00-\u9fff]/.test(p.value.content)) console.log('ATTR', p.name, JSON.stringify(p.value.content), p.loc.start.offset, p.loc.end.offset) }
  for (const c of n.children||[]) walk(c, depth+1)
}
walk(tpl.ast)
