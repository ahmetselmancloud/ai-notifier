alter table devices add column if not exists fcm_token text;

create policy "authenticated can update own device fcm token"
  on devices for update
  to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create or replace function get_fcm_token_for_desktop(p_desktop_instance_id text)
returns text
language sql
security definer
set search_path = public
as $$
  select fcm_token from devices where desktop_instance_id = p_desktop_instance_id limit 1;
$$;

grant execute on function get_fcm_token_for_desktop(text) to anon;
