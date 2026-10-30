# Home DNS

The mini runs dnsmasq using `hosts/nixos-btw/dns.nix`. The Speedport Smart 4 Plus forwards DNS queries to it; clients continue to use the router as their DNS server.

## Configuration

| Item | Value |
| --- | --- |
| Mini LAN interface | `enp1s0f0` |
| Mini reserved IPv4 address | `192.168.2.76` |
| Mini stable IPv6 ULA | `fdbb:5674:2c0f:1::53/64` |
| Router IPv4 address | `192.168.2.1` |
| Router ULA prefix | `fdbb:5674:2c0f:1::/64` |
| Local records | `immich.home.arpa` and `monitor.home.arpa` → `192.168.2.76` |
| Upstream DNS | Quad9: `9.9.9.9`, `149.112.112.112` |

Dnsmasq listens on the LAN interface and loopback; the firewall allows DNS over UDP and TCP on the LAN interface. It forwards queries directly to Quad9 rather than using the router as an upstream, avoiding a forwarding loop. The `home.arpa` zone is local and unknown names are not forwarded. Mini's own NetworkManager resolver settings remain unchanged.

The Speedport has ULA enabled and its preferred DNSv4 and DNSv6 servers set to the mini's IPv4 and ULA addresses above. It reserves the IPv4 address for the mini. Devices using VPNs, private DNS, browser secure DNS, or guest Wi-Fi may bypass or be unable to reach this resolver.

## Verify

On the mini:

```sh
systemctl status dnsmasq --no-pager
ip -br address show enp1s0f0
nmcli -g ipv6.method,ipv6.addresses connection show "Wired connection 1"
```

From a LAN client with `dig`:

```sh
dig @192.168.2.76 immich.home.arpa A
dig -6 @fdbb:5674:2c0f:1::53 monitor.home.arpa A
dig @192.168.2.1 immich.home.arpa A
dig @192.168.2.1 example.com A
```

The local names should return `192.168.2.76`; `example.com` checks internet forwarding. Also test `http://immich.home.arpa` from a phone on the main Wi-Fi. Direct IPv4 and IPv6 queries to the mini and IPv4 queries through the router have been verified; router-side IPv6 DNS forwarding still needs a separate end-to-end check.

## Recovery and changes

The IPv6 ULA is saved in the NetworkManager connection profile, **not declared in NixOS**. On a fresh install or replacement profile, first verify the connection name, interface, router ULA prefix, and that the address is unused. Then restore it with:

```sh
sudo nmcli connection modify "Wired connection 1" \
  +ipv6.addresses "fdbb:5674:2c0f:1::53/64"
sudo nmcli device reapply enp1s0f0
```

If reapply fails, investigate before reconnecting the interface, as doing so can interrupt SSH. Confirm `ipv6.method` remains `auto`. If the router's ULA prefix or mini's reserved IPv4 address changes, update the NetworkManager address, `dns.nix` records, and Speedport preferred DNS settings together. Test the new addresses directly before changing the router.

Mini is currently the only DNS resolver for the household. If it is down, internet DNS may stop working. To restore general internet resolution, revert the Speedport's preferred DNSv4 and DNSv6 settings to its defaults. Local `home.arpa` names will not resolve through public DNS. A second resolver would need the same local records; using a public DNS server as secondary can cause intermittent local-name failures.

If local names resolve directly against mini but not through the Speedport, check its DNS rebind protection and add a narrowly scoped exception only if necessary. No exception was needed for the verified IPv4 queries.
