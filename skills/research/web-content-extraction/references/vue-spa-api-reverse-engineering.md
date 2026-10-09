# Reverse-Engineering a Query-Form SPA's Hidden JSON API

Worked example: pulling 广发银行 (China Guangfa Bank) "合作机构查询" full partner list
(`https://inss.cgbchina.com.cn/inss/partnersQuery/index.html`), which is a Vue SPA that
shows nothing until you type a name and click 查询. `web_extract` returned only the empty
form shell.

## Steps

1. Fetch HTML and list JS bundles:
   ```bash
   curl -sL --max-time 20 URL -o /tmp/page.html
   grep -oE 'src="[^"]*\.js"' /tmp/page.html
   # note: page-specific bundle + config.js + common bundle
   ```
   Output showed `partnersQuery/index.6c681511.js`, `config.js`, `common.dde465ec.js`.

2. Download the page-specific bundle and grep for API path patterns:
   ```bash
   curl -sL .../index.6c681511.js -o /tmp/app.js
   python3 - <<'PY'
   js = open('/tmp/app.js').read()
   idx = js.find('Rtp.http')
   while idx != -1:
       print(js[idx:idx+350]); print('======')
       idx = js.find('Rtp.http', idx+1)
   PY
   ```
   Found: `Rtp.http("noSessionServlet/cooperativeAgency/selectPageCooperativeAgencyInfo.fun", ...)`
   The request object also shows the payload keys (`beginNum`, `fetchNum`, `partnerOrgName`).

3. Find `baseURL` — usually in `config.js` or the common bundle:
   ```bash
   curl -sL .../static/config.js   # window.gConfig — no baseURL here
   grep -oE 'baseURL[^,;]{0,120}' /tmp/cgb_common.js   # -> baseURL:"/inss/insswebapp"
   ```
   Full endpoint: `https://inss.cgbchina.com.cn/inss/insswebapp/noSessionServlet/cooperativeAgency/selectPageCooperativeAgencyInfo.fun`

4. First attempt at raw body failed with `404` because baseURL was missing. With baseURL
   included, server returned:
   `{"header":{"errorCode":"IN9999","errorMsg":"\"request must has header,such as {\"header:{}}\""}}`
   → wrap payload: `{"header":{},"body":{...}}`

5. Working call:
   ```bash
   curl -s -X POST "https://inss.cgbchina.com.cn/inss/insswebapp/noSessionServlet/cooperativeAgency/selectPageCooperativeAgencyInfo.fun" \
     -H "Content-Type: application/json" \
     -H "Referer: https://inss.cgbchina.com.cn/inss/partnersQuery/index.html" \
     -d '{"header":{},"body":{"beginNum":0,"fetchNum":100,"partnerOrgName":""}}'
   ```

6. Pagination: `fetchNum:500` was rejected with
   `{"errorCode":"rtp_data_bind_err","errorMsg":"fetchNum: must be less than or equal to 200"}`.
   Loop `beginNum` in chunks of 100–200, merge results.

## Pitfalls

- The `Rtp.http` string is inside the *page-specific* bundle, not vendor.js — grep the
  right file, or grep all bundles.
- `baseURL` may live in `config.js` OR a common bundle — check both.
- Server error messages are descriptive here ("must has header", "must be less than or
  equal to 200") — read them and adapt; they tell you the exact contract.
- Send `Referer` matching the page — some servers 403/404 direct calls.
- Large lists are paginated server-side; never assume a single call returns everything.
