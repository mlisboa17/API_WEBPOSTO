import { formatPeriodBr, isoDateToBr } from "../services/format.js";



const PRESETS = [

  { id: "today", label: "Hoje" },

  { id: "yesterday", label: "Ontem" },

  { id: "last7", label: "Últimos 7 dias" },

  { id: "last30", label: "Últimos 30 dias" },

  { id: "thisMonth", label: "Este mês" },

  { id: "prevMonth", label: "Mês anterior" },

];



function pad(n) {

  return String(n).padStart(2, "0");

}



function toIsoDate(d) {

  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

}



function parseIso(iso) {

  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;

  const [y, m, d] = iso.split("-").map(Number);

  return new Date(y, m - 1, d);

}



function startOfDay(d) {

  return new Date(d.getFullYear(), d.getMonth(), d.getDate());

}



function addDays(d, n) {

  const x = new Date(d);

  x.setDate(x.getDate() + n);

  return x;

}



function presetRange(id) {

  const today = startOfDay(new Date());

  switch (id) {

    case "today":

      return [today, today];

    case "yesterday": {

      const y = addDays(today, -1);

      return [y, y];

    }

    case "last7":

      return [addDays(today, -6), today];

    case "last30":

      return [addDays(today, -29), today];

    case "thisMonth":

      return [new Date(today.getFullYear(), today.getMonth(), 1), today];

    case "prevMonth": {

      const start = new Date(today.getFullYear(), today.getMonth() - 1, 1);

      const end = new Date(today.getFullYear(), today.getMonth(), 0);

      return [start, end];

    }

    default:

      return [today, today];

  }

}



function monthMatrix(year, month) {

  const first = new Date(year, month, 1);

  const startWeekday = first.getDay();

  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells = [];

  for (let i = 0; i < startWeekday; i++) cells.push(null);

  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));

  while (cells.length % 7 !== 0) cells.push(null);

  return cells;

}



function inRange(day, start, end) {

  if (!day || !start || !end) return false;

  const t = day.getTime();

  return t >= start.getTime() && t <= end.getTime();

}



function sameDay(a, b) {

  return a && b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

}



const MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];



export function mountDateRangePicker(host, { dataInicial, dataFinal }, onApply) {

  if (!host) return null;



  let start = parseIso(dataInicial) || startOfDay(new Date());

  let end = parseIso(dataFinal) || start;

  if (start > end) end = start;

  let draftStart = start;

  let draftEnd = end;

  let selectionStep = "start";

  let viewYear = end.getFullYear();

  let viewMonth = end.getMonth();

  let open = false;



  host.innerHTML = `

    <div class="drp">

      <button type="button" class="drp-trigger" aria-haspopup="dialog" aria-expanded="false">

        <span class="drp-trigger__icon" aria-hidden="true">📅</span>

        <span class="drp-trigger__label">Período</span>

        <span class="drp-trigger__value"></span>

        <span class="drp-trigger__chev" aria-hidden="true">▾</span>

      </button>

      <div class="drp-popover hidden" role="dialog" aria-label="Selecionar período">

        <div class="drp-popover__presets"></div>

        <div class="drp-popover__calendar">

          <div class="drp-cal-header">

            <button type="button" class="drp-nav" data-nav="prev" aria-label="Mês anterior">‹</button>

            <strong class="drp-cal-title"></strong>

            <button type="button" class="drp-nav" data-nav="next" aria-label="Próximo mês">›</button>

          </div>

          <div class="drp-weekdays"><span>D</span><span>S</span><span>T</span><span>Q</span><span>Q</span><span>S</span><span>S</span></div>

          <div class="drp-grid"></div>

        </div>

        <div class="drp-popover__footer">

          <span class="drp-draft-label"></span>

          <button type="button" class="btn-secondary drp-cancel">Cancelar</button>

          <button type="button" class="btn-primary drp-apply">Aplicar</button>

        </div>

      </div>

    </div>

  `;



  const trigger = host.querySelector(".drp-trigger");

  const popover = host.querySelector(".drp-popover");

  const valueEl = host.querySelector(".drp-trigger__value");

  const presetsEl = host.querySelector(".drp-popover__presets");

  const gridEl = host.querySelector(".drp-grid");

  const titleEl = host.querySelector(".drp-cal-title");

  const draftLabel = host.querySelector(".drp-draft-label");

  const abort = new AbortController();

  const { signal } = abort;



  popover.addEventListener("click", (e) => e.stopPropagation(), { signal });

  popover.addEventListener("mousedown", (e) => e.stopPropagation(), { signal });



  function syncTrigger() {

    valueEl.textContent = formatPeriodBr(toIsoDate(start), toIsoDate(end));

  }



  function draftHint() {

    if (selectionStep === "end") {

      return "Clique na data final do período";

    }

    if (draftStart && draftEnd && !sameDay(draftStart, draftEnd)) {

      return "Intervalo pronto — clique Aplicar ou escolha nova data inicial";

    }

    return "Clique na data inicial do período";

  }



  function renderPresets() {

    presetsEl.innerHTML = PRESETS.map(

      (p) => `<button type="button" class="drp-preset" data-preset="${p.id}">${p.label}</button>`

    ).join("");

  }



  function renderCalendar() {

    titleEl.textContent = `${MONTHS[viewMonth]} ${viewYear}`;

    const cells = monthMatrix(viewYear, viewMonth);

    gridEl.innerHTML = cells

      .map((day) => {

        if (!day) return `<span class="drp-day drp-day--empty"></span>`;

        const isRangeStart = draftStart && sameDay(day, draftStart);

        const isRangeEnd = draftEnd && sameDay(day, draftEnd);

        const inBand = draftEnd && inRange(day, draftStart, draftEnd);

        const isToday = sameDay(day, startOfDay(new Date()));

        return `

          <button

            type="button"

            class="drp-day${isRangeStart ? " drp-day--range-start" : ""}${isRangeEnd ? " drp-day--range-end" : ""}${inBand ? " drp-day--in-range" : ""}${isToday ? " drp-day--today" : ""}"

            data-iso="${toIsoDate(day)}"

          >${day.getDate()}</button>`;

      })

      .join("");



    if (draftStart && draftEnd) {

      draftLabel.textContent = `${isoDateToBr(toIsoDate(draftStart))} — ${isoDateToBr(toIsoDate(draftEnd))} · ${draftHint()}`;

    } else if (draftStart) {

      draftLabel.textContent = `${isoDateToBr(toIsoDate(draftStart))} — … · ${draftHint()}`;

    } else {

      draftLabel.textContent = draftHint();

    }

  }



  function openPopover() {

    draftStart = start;

    draftEnd = end;

    selectionStep = "start";

    viewYear = end.getFullYear();

    viewMonth = end.getMonth();

    open = true;

    popover.classList.remove("hidden");

    trigger.setAttribute("aria-expanded", "true");

    renderCalendar();

  }



  function closePopover() {

    open = false;

    popover.classList.add("hidden");

    trigger.setAttribute("aria-expanded", "false");

  }



  trigger.addEventListener(

    "click",

    (e) => {

      e.stopPropagation();

      if (open) closePopover();

      else openPopover();

    },

    { signal }

  );



  presetsEl.addEventListener(

    "click",

    (e) => {

      e.stopPropagation();

      const btn = e.target.closest("[data-preset]");

      if (!btn) return;

      const [s, en] = presetRange(btn.dataset.preset);

      draftStart = s;

      draftEnd = en;

      selectionStep = "start";

      viewYear = en.getFullYear();

      viewMonth = en.getMonth();

      renderCalendar();

    },

    { signal }

  );



  gridEl.addEventListener(

    "click",

    (e) => {

      e.stopPropagation();

      const btn = e.target.closest(".drp-day[data-iso]");

      if (!btn) return;

      const day = parseIso(btn.dataset.iso);

      if (!day) return;



      if (selectionStep === "start") {

        draftStart = day;

        draftEnd = day;

        selectionStep = "end";

      } else {

        if (day < draftStart) {

          draftEnd = draftStart;

          draftStart = day;

        } else {

          draftEnd = day;

        }

        selectionStep = "start";

      }

      renderCalendar();

    },

    { signal }

  );



  host.querySelector('[data-nav="prev"]')?.addEventListener(

    "click",

    (e) => {

      e.stopPropagation();

      viewMonth -= 1;

      if (viewMonth < 0) {

        viewMonth = 11;

        viewYear -= 1;

      }

      renderCalendar();

    },

    { signal }

  );



  host.querySelector('[data-nav="next"]')?.addEventListener(

    "click",

    (e) => {

      e.stopPropagation();

      viewMonth += 1;

      if (viewMonth > 11) {

        viewMonth = 0;

        viewYear += 1;

      }

      renderCalendar();

    },

    { signal }

  );



  host.querySelector(".drp-cancel")?.addEventListener(

    "click",

    (e) => {

      e.stopPropagation();

      closePopover();

    },

    { signal }

  );



  host.querySelector(".drp-apply")?.addEventListener(

    "click",

    (e) => {

      e.stopPropagation();

      if (!draftStart) return;

      if (!draftEnd) draftEnd = draftStart;

      if (draftStart > draftEnd) draftEnd = draftStart;

      start = draftStart;

      end = draftEnd;

      syncTrigger();

      closePopover();

      onApply?.({ dataInicial: toIsoDate(start), dataFinal: toIsoDate(end) });

    },

    { signal }

  );



  document.addEventListener(

    "click",

    (e) => {

      if (!open) return;

      if (host.contains(e.target)) return;

      closePopover();

    },

    { signal }

  );



  renderPresets();

  syncTrigger();



  return {

    getRange: () => ({ dataInicial: toIsoDate(start), dataFinal: toIsoDate(end) }),

    setRange: (ini, fin) => {

      start = parseIso(ini) || start;

      end = parseIso(fin) || end;

      if (start > end) end = start;

      syncTrigger();

    },

    destroy: () => abort.abort(),

  };

}

