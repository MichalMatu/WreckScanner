# Publiczny Runtime

## Lokalny uklad portow

Na Raspberry Pi kazda aplikacja ma osobny lokalny port:

```text
PhotoMap    http://127.0.0.1:8000
IleStoi.pl  http://127.0.0.1:8001
```

Sprawdzenie:

```bash
systemctl status photomap.service wreckscanner.service cloudflared.service --no-pager
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8001/api/health/live
curl -fsS http://127.0.0.1:8001/api/health/ready
```

`live` potwierdza dzialanie procesu; do kierowania ruchu przez tunel wymagaj
odpowiedzi `200` z `ready`.

## Jeden tunel, wiele hostow

Jeden `cloudflared` na tym samym Raspberry Pi moze obslugiwac kilka publicznych hostname'ow. Dla kazdej strony dodaj osobny wpis DNS/CNAME w Cloudflare i osobny wpis `ingress` w `/etc/cloudflared/config.yml`.

Przyklad konfiguracji:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /home/test/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: photomap.pl
    service: http://127.0.0.1:8000
  - hostname: www.photomap.pl
    service: http://127.0.0.1:8000
  - hostname: wreckscanner.pl
    service: http://127.0.0.1:8001
  - hostname: www.wreckscanner.pl
    service: http://127.0.0.1:8001
  - hostname: ilestoi.pl
    service: http://127.0.0.1:8001
  - hostname: www.ilestoi.pl
    service: http://127.0.0.1:8001
  - hostname: dlugostoi.pl
    service: http://127.0.0.1:8001
  - hostname: www.dlugostoi.pl
    service: http://127.0.0.1:8001
  - service: http_status:404
```

Po zmianie konfiguracji:

```bash
cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate
sudo systemctl restart cloudflared.service
systemctl status cloudflared.service --no-pager
```

Nie restartuj tunelu, jesli walidacja ingress nie zakonczy sie wynikiem `OK`.
Dla kazdego hostname'u utworz odpowiadajacy, proxied rekord Tunnel/CNAME w DNS.

Backend honoruje `X-Forwarded-Proto` tylko od adresow z
`WRECKSCANNER_TRUSTED_PROXY_ADDRESSES`. `ilestoi.pl` jest jedynym hostem
kanonicznym. Publiczne zadanie HTTP oraz kazde zadanie do aliasu
`wreckscanner.pl`, `dlugostoi.pl` albo wariantu `www` dostaje jeden `308` do
tej samej sciezki pod `https://ilestoi.pl`. Wszystkie aliasy musza pozostac w
DNS i ingress tunelu, aby stare linki oraz boty otrzymywaly przekierowanie.
Bezposrednie lokalne health-checki bez naglowka proxy nadal dzialaja po HTTP.

Po wdrozeniu zmiany domeny sprawdz:

```bash
curl -sSI http://wreckscanner.pl/ | sed -n '1p;/^location:/Ip'
curl -sSI https://dlugostoi.pl/ | sed -n '1p;/^location:/Ip'
curl -fsS https://ilestoi.pl/robots.txt
curl -fsS https://ilestoi.pl/sitemap.xml
```

W Google Search Console zweryfikuj stara i nowa domene, zglos zmiane adresu na
`ilestoi.pl`, dodaj `https://ilestoi.pl/sitemap.xml` i popros o ponowne
zindeksowanie strony glownej.

Usuniecie strony oznacza usuniecie jej wpisow `ingress`, usuniecie jej rekordow DNS w Cloudflare i zatrzymanie/wylaczenie jej uslugi systemd.
