function qs(id){return document.getElementById(id)}
const fileInput=qs('fileInput'), previewBtn=qs('previewBtn'), importBtn=qs('importBtn')
let parsedRows=[], headers=[]

fileInput.addEventListener('change',()=>{
  previewBtn.disabled = !fileInput.files.length
})

previewBtn.addEventListener('click',()=>{
  const f = fileInput.files[0]
  if(!f) return
  const reader = new FileReader()
  reader.onload = e => handleCSV(e.target.result)
  reader.readAsText(f, 'UTF-8')
})

function handleCSV(text){
  const lines = text.split(/\r?\n/).filter(Boolean)
  if(!lines.length) return alert('Arquivo vazio')
  headers = splitCSVLine(lines[0])
  parsedRows = lines.slice(1).map(l=>{
    const values = splitCSVLine(l)
    const obj = {}
    headers.forEach((h,i)=>obj[h]=values[i]===undefined?"":values[i])
    return obj
  })
  renderPreview(headers, parsedRows)
}

function splitCSVLine(line){
  // parser CSV simples (não cobre todos os casos) — suficiente para protótipo
  const out=[]
  let cur='', inQuotes=false
  for(let i=0;i<line.length;i++){
    const ch=line[i]
    if(ch==='"') { inQuotes=!inQuotes; continue }
    if(ch===',' && !inQuotes){ out.push(cur.trim()); cur=''; continue }
    cur+=ch
  }
  out.push(cur.trim())
  return out
}

function renderPreview(h, rows){
  qs('summary').classList.remove('hidden')
  qs('preview').classList.remove('hidden')
  qs('validation').classList.remove('hidden')
  qs('rowsCount').textContent = `${rows.length} linhas detectadas`
  const errors=[]
  // validações simples: campo vazio e email inválido se existir coluna 'email'
  const emailCol = h.find(col=>col.toLowerCase().includes('email'))
  rows.forEach((r,idx)=>{
    const rowErrors=[]
    h.forEach(col=>{ if(r[col]==='') rowErrors.push(`${col} vazio`) })
    if(emailCol){
      const v=r[emailCol]||''
      if(v && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) rowErrors.push('email inválido')
    }
    if(rowErrors.length) errors.push({idx:idx+2, details:rowErrors})
  })
  qs('errorsCount').textContent = `${errors.length} linhas com erros`
  renderTable(h, rows, errors)
  renderErrors(errors)
  importBtn.disabled = false
}

function renderTable(h, rows, errors){
  const thead = qs('previewHead'); const tbody=qs('previewBody');
  thead.innerHTML = '<tr>'+h.map(x=>`<th>${escapeHtml(x)}</th>`).join('')+'</tr>'
  tbody.innerHTML = ''
  const max = Math.min(rows.length, 50) // preview até 50 linhas
  for(let i=0;i<max;i++){
    const row = rows[i]
    const tr = document.createElement('tr')
    const err = errors.find(e=>e.idx===i+2)
    if(err) tr.classList.add('row-error')
    h.forEach(col=>{ const td=document.createElement('td'); td.textContent=row[col]||''; tr.appendChild(td) })
    tbody.appendChild(tr)
  }
}

function renderErrors(errors){
  const ul=qs('errorList'); ul.innerHTML=''
  if(!errors.length) { ul.innerHTML='<li>Nenhum erro detectado</li>'; return }
  errors.forEach(e=>{ const li=document.createElement('li'); li.textContent=`Linha ${e.idx}: ${e.details.join('; ')}`; ul.appendChild(li) })
}

function escapeHtml(s){ return (s+'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])) }

importBtn.addEventListener('click',()=>{
  startImportSimulation(parsedRows)
})

function startImportSimulation(rows){
  qs('progressSection').classList.remove('hidden')
  const total = rows.length
  let done = 0
  const interval = setInterval(()=>{
    done += Math.min(5, total-done)
    const pct = Math.round((done/total)*100)
    qs('progressBar').style.width = pct + '%'
    qs('progressText').textContent = `${done}/${total} linhas processadas (${pct}%)`
    if(done>=total){ clearInterval(interval); qs('progressText').textContent = `Importação concluída: ${total} linhas` }
  }, 350)
}
