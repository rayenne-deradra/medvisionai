-- MedVisionAI appointment requests. Run once in Supabase: Project -> SQL Editor -> New query -> paste -> Run.
create table if not exists public.appointments (
  id              uuid primary key default gen_random_uuid(),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  licence_id      text not null,
  organisation    text not null default '',
  requester_name  text not null,
  contact         text not null,
  hospital        text not null default '',
  department      text not null default '',
  specialist      text not null,
  urgency         text not null check (urgency in ('urgent', 'soon', 'routine')),
  priority        smallint not null check (priority between 1 and 3),
  reason          text not null,
  preferred       text not null default '',
  patient_ref     text not null default '',
  case_summary    text not null default '',
  status          text not null default 'pending'
                  check (status in ('pending', 'confirmed', 'declined', 'completed', 'cancelled')),
  appointment_at  timestamptz,
  location        text not null default '',
  staff_note      text not null default ''
);

create index if not exists appointments_queue on public.appointments (status, priority, created_at);
create index if not exists appointments_licence on public.appointments (licence_id);

-- Only the app (server side, service-role key) may read or write: with row level security on and no policies,
-- the public "anon" key cannot access any row.
alter table public.appointments enable row level security;
