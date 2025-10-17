# Remote Control Protocol & Testing Notes

## Protocol Overview

- **Screen streaming:**
  - Client connects to server (ServerScreen) on SCREEN_PORT, sends handshake `b"CLNT:"`, then repeatedly sends:
    - 12-byte header: `struct.pack('>III', width, height, length)`
    - JPEG image bytes (length bytes)
  - Manager connects to server (ServerScreen) on SCREEN_PORT, sends handshake `b"MGR:"`, then receives the same header+JPEG stream as above.

- **Input control:**
  - Manager sends JSON events (mouse/keyboard) as lines (ending with `\n`) to server on CONTROL_PORT.
  - Server relays these lines to all connected clients on CLIENT_PORT.
  - Client parses each JSON line and applies the event using pynput.

## Coordinate Mapping

- ManagerViewer computes `scale_x` and `scale_y` as:
  - `scale_x = remote_width / label.width()`
  - `scale_y = remote_height / label.height()`
- ManagerInput uses these to map local mouse coordinates to remote screen coordinates.
- Client applies received coordinates as absolute positions (relative to primary monitor).

## Testing Steps

1. **Start server:**
   - Run `python src/client/server.py`
2. **Start client:**
   - Run `python src/client/client.py` on the remote machine.
3. **Start manager:**
   - Run `python src/client/manager.py` on the controlling machine.
4. **Verify:**
   - Manager window shows live screen from client.
   - Mouse/keyboard actions in manager window are reflected on client.

## Troubleshooting

- If manager window is black or not updating, check handshake (`b"MGR:"`) is sent after connect.
- If mouse control is offset, check that scale_x/scale_y are computed and used as above.
- If input is not working, check server logs for connection and forwarding errors.

## Security Note
- This protocol is for demo/learning. For real-world use, add authentication and encryption (TLS).
