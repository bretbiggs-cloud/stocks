# Homelab Routing and Network Topology Reference

## Network Architecture & IP Plan

| Subnet / Network | Type | Gateway / Host Interface | Allocated IPs / Purpose |
| :--- | :--- | :--- | :--- |
| `192.0.2.0/24` | Physical LAN | `192.0.2.1` | - `192.0.2.3`: UGREEN NAS Host OS (`nas.example.invalid`)<br>- `192.0.2.4`: Caddy Reverse Proxy (`*.example.invalid`) via `external_npm` macvlan<br>- `192.0.2.2`: Pi-hole DNS resolver |
| `198.51.100.0/24` | Docker Bridge (`homelab`) | `198.51.100.1` (docker bridge) | - All backend containers communicate internally on this bridge.<br>- Caddy bridges both `external_npm` and `homelab`. |
| `100.64.0.0/10` | Tailscale CGNAT | Tun device (`tailscale0`) | - Encrypted mesh overlay.<br>- Subnet routing and exit node traffic via `vpn-bridge`. |

---

## Reverse Proxy (Caddy Docker Proxy) Dynamic Routing

Caddy discovers routing configurations dynamically from container labels over the Docker socket `/var/run/docker.sock`. Wildcard certificates are provisioned automatically via Cloudflare DNS-01 ACME.

### Inspecting Dynamic Routes:
```bash
docker exec caddy curl -s http://localhost:2019/config/apps/http/servers/srv0/routes | jq .
```

### Key Service Mappings:
- `homepage.example.invalid` -> Homepage (`homepage:3000`)
- `dockge.example.invalid` -> Dockge (`dockge:5001`)
- `jellyfin.example.invalid` -> Jellyfin (`jellyfin:8096`)
- `seerr.example.invalid` -> Seerr (`seerr:5055`)
- `recipes.example.invalid` -> Mealie (`mealie:9000`)
- `sonarr.example.invalid` -> Sonarr (`sonarr:8989`)
- `radarr.example.invalid` -> Radarr (`radarr:7878`)
- `prowlarr.example.invalid` -> Prowlarr (`prowlarr:9696`)
- `torrent.example.invalid` -> qBittorrent (`qbittorrentvpn:8081`)
- `download.example.invalid` -> Caddy File Delivery (`/downloads`)
- `nas.example.invalid` -> UGOS Host Portal (`198.51.100.1:9999`)

---

## Macvlan Host-to-Container Isolation Caveat

Under Linux macvlan networking, the host OS kernel explicitly prevents direct communication between the physical parent interface (`eth0` on `192.0.2.3`) and child macvlan endpoints (`192.0.2.4`) over the parent device.

### Implications:
1. Probing `192.0.2.4` directly from the NAS host shell (`curl https://192.0.2.4`) may fail or time out unless a macvlan bridge shim (`macvlan-shim`) is configured on the host.
2. The automated smoke tests impersonate client requests by probing Caddy's container IP directly or routing via bridge adapters:
   ```bash
   curl -skL -H "Host: jellyfin.example.invalid" "https://${NPM_IPV4_ADDRESS}"
   ```

---

## VPN and Killswitch Architecture (`vpn-bridge` & `qbittorrentvpn`)

### Gluetun WireGuard (PIA):
- Inbound traffic to forwarded services must be allowed through `FIREWALL_VPN_INPUT_PORTS` and `LOCAL_NETWORK`.
- `LOCAL_NETWORK` must encompass LAN subnets (`192.0.2.0/24`, `198.51.100.0/24`), but **MUST NOT** include `100.64.0.0/10` to prevent Tailscale routing loops.
- `VPNDNS` uses Quad9 (`9.9.9.9,149.112.112.112`).

### Tailscale Exit Node & Subnet Routing:
- Forwarding rules are applied to container iptables:
  ```bash
  iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE
  iptables -A FORWARD -i tailscale0 -o tun0 -j ACCEPT
  iptables -A FORWARD -i tun0 -o tailscale0 -m state --state RELATED,ESTABLISHED -j ACCEPT
  ```
- Subnet routes advertised: `192.0.2.0/24,198.51.100.0/24`.
