create table if not exists pairing_codes (
  code text primary key,
  desktop_instance_id text not null,
  status text not null default 'pending' check (status in ('pending', 'claimed')),
  claimed_by_user_id uuid references auth.users(id),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);

create table if not exists devices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  desktop_instance_id text not null,
  paired_at timestamptz not null default now()
);

alter table pairing_codes enable row level security;
alter table devices enable row level security;

-- anon (masaüstü servisi): bekleyen bir eşleştirme kodu oluşturabilir
create policy "anon can insert pending pairing codes"
  on pairing_codes for insert
  to anon
  with check (status = 'pending' and claimed_by_user_id is null);

-- anon: kodun durumunu okuyabilir (kod zaten rastgele/gizli, kısa ömürlü)
create policy "anon can read pairing codes"
  on pairing_codes for select
  to anon
  using (true);

-- authenticated (telefon): bekleyen, süresi dolmamış bir kodu claim edebilir
create policy "authenticated users can claim pending codes"
  on pairing_codes for update
  to authenticated
  using (status = 'pending' and expires_at > now())
  with check (status = 'claimed' and claimed_by_user_id = auth.uid());

-- authenticated: kendi cihaz kaydını ekleyebilir/okuyabilir
create policy "users can insert their own device"
  on devices for insert
  to authenticated
  with check (user_id = auth.uid());

create policy "users can read their own devices"
  on devices for select
  to authenticated
  using (user_id = auth.uid());
