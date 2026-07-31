from pathlib import Path

p = Path("backend/app.py")

if not p.exists():
    raise RuntimeError("backend/app.py não encontrado.")

s = p.read_text(encoding="utf-8")

Path("backend/app_backup_corrigir_meta_comercial_insights.py").write_text(s, encoding="utf-8")

old_normalize = '''function normalizeAccounts(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.accounts)) return data.accounts;
  if (Array.isArray(data.data)) return data.data;
  if (Array.isArray(data.connected_accounts)) return data.connected_accounts;
  if (data.account) return [data.account];
  return [];
}'''

new_normalize = '''function normalizeAccounts(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.accounts)) return data.accounts;
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.data)) return data.data;
  if (Array.isArray(data.results)) return data.results;
  if (Array.isArray(data.connected_accounts)) return data.connected_accounts;
  if (data.account) return [data.account];
  return [];
}'''

old_account_id = '''function accountId(acc) {
  return acc.id || acc.account_id || acc.connected_account_id || acc.row_id || acc.db_id;
}'''

new_account_id = '''function accountId(acc) {
  return (
    acc.id ||
    acc.account_id ||
    acc.connected_account_id ||
    acc.row_id ||
    acc.db_id ||
    acc.meta_account_id ||
    acc.instagram_business_account_id ||
    acc.ig_user_id ||
    acc.instagram_id ||
    acc.page_id
  );
}'''

old_error = '''if (!id) {
    alert("Não localizei o ID interno da conta conectada.");
    return;
  }'''

new_error = '''if (!id) {
    document.getElementById("diagnosis").innerHTML = "Não localizei o ID interno da conta conectada.";
    document.getElementById("raw").textContent = JSON.stringify(selectedAccount, null, 2);
    alert("Não localizei o ID interno da conta conectada. Veja os dados técnicos na tela.");
    return;
  }'''

old_fetch = '''const res = await fetch(`/api/meta-connected/accounts/${encodeURIComponent(id)}/insights`, {
      credentials: "include"
    });

    const data = await res.json();

    if (!res.ok) {
      document.getElementById("diagnosis").innerHTML = "Erro ao gerar insights.";
      document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
      return;
    }'''

new_fetch = '''const url = `/api/meta-connected/accounts/${encodeURIComponent(id)}/insights`;

    const res = await fetch(url, {
      credentials: "include"
    });

    const data = await res.json();

    if (!res.ok) {
      document.getElementById("diagnosis").innerHTML = "Erro ao gerar insights. Veja os dados técnicos abaixo.";
      document.getElementById("raw").textContent = JSON.stringify({
        endpoint_usado: url,
        id_usado: id,
        conta_selecionada: selectedAccount,
        erro: data
      }, null, 2);
      return;
    }'''

if old_normalize in s:
    s = s.replace(old_normalize, new_normalize, 1)

if old_account_id in s:
    s = s.replace(old_account_id, new_account_id, 1)

if old_error in s:
    s = s.replace(old_error, new_error, 1)

if old_fetch in s:
    s = s.replace(old_fetch, new_fetch, 1)

p.write_text(s, encoding="utf-8")

print("Correção da página Meta Comercial aplicada.")
print("items suportado?", "Array.isArray(data.items)" in s)
print("erro detalhado instalado?", "endpoint_usado" in s)
