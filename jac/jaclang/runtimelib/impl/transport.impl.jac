impl TransportResponse.success(
    data: any = None,
    msg_type: MessageType = MessageType.RESPONSE,
    meta: (Meta | None) = None
) -> TransportResponse {
    final_meta = meta or Meta();
    response = TransportResponse();
    response.type = msg_type.value if isinstance(msg_type, MessageType) else msg_type;
    response.ok = True;
    response.data = data;
    response.error = None;
    response.meta = final_meta;
    return response;
}

impl TransportResponse.fail(
    code: str,
    message: str,
    details: any = None,
    msg_type: MessageType = MessageType.ERROR,
    meta: (Meta | None) = None
) -> TransportResponse {
    final_meta = meta or Meta();
    response = TransportResponse();
    response.type = msg_type.value if isinstance(msg_type, MessageType) else msg_type;
    response.ok = False;
    response.data = None;
    response.error = ErrorInfo(code=code, message=message, details=details);
    response.meta = final_meta;
    return response;
}

impl HTTPTransport.send(data: any) -> None {
    if isinstance(data, TransportResponse) {
        status = data.meta.extra.get('http_status', 200 if data.ok else 500)
            if data.meta.extra
            else (200 if data.ok else 500);

        import from jaclang.runtimelib.utils { lean_response_enabled }
        if (
            lean_response_enabled()
            and data.ok
            and isinstance(data.data, dict)
            and isinstance(data.data.get('server_total_ms'), (int, float))
        ) {
            # Lean bench contract: the lone report is the whole body; the
            # walker-stamped timings ride as headers instead of payload.
            lean_body = dict(data.data);
            ms = lean_body.pop('server_total_ms');
            self.handler.send_response(status);
            self.handler.send_header('Content-Type', 'application/json');
            self.handler.send_header('x-server-total-ms', f"{ms:.3f}");
            ser_ms = lean_body.pop('server_serialize_ms', None);
            if isinstance(ser_ms, (int, float)) {
                self.handler.send_header('x-server-serialize-ms', f"{ser_ms:.3f}");
            }
            self.handler.send_header('Access-Control-Allow-Origin', '*');
            self.handler.send_header(
                'Access-Control-Allow-Methods', 'GET, POST, OPTIONS'
            );
            self.handler.send_header(
                'Access-Control-Allow-Headers', 'Content-Type, Authorization'
            );
            self.handler.end_headers();
            self.handler.wfile.write(json.dumps(lean_body).encode());
            self.response_data = lean_body;
            if self.on_message {
                self.on_message(data);
            }
            return;
        }

        response_body = {
            'ok': data.ok,
            'type': data.type,
            'data': data.data,
            'error': None
        };

        if not data.ok and data.error {
            error_obj = {};
            if data.error.code {
                error_obj['code'] = data.error.code;
            }
            if data.error.message {
                error_obj['message'] = data.error.message;
            }
            if data.error.details is not None {
                error_obj['details'] = data.error.details;
            }
            response_body['error'] = error_obj;
        }

        if data.meta {
            meta_dict = {};
            if data.meta.request_id {
                meta_dict['request_id'] = data.meta.request_id;
            }
            if data.meta.trace_id {
                meta_dict['trace_id'] = data.meta.trace_id;
            }
            if data.meta.timestamp {
                meta_dict['timestamp'] = data.meta.timestamp;
            }
            if data.meta.extra {
                meta_dict['extra'] = data.meta.extra;
            }
            if meta_dict {
                response_body['meta'] = meta_dict;
            }
        }

        self.handler.send_response(status);
        self.handler.send_header('Content-Type', 'application/json');
        self.handler.send_header('Access-Control-Allow-Origin', '*');
        self.handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        self.handler.send_header(
            'Access-Control-Allow-Headers', 'Content-Type, Authorization'
        );
        self.handler.end_headers();
        self.handler.wfile.write(json.dumps(response_body).encode());

        self.response_data = response_body;
    } else {
        self.response_data.update(data) if isinstance(data, dict) else None;
        self.response_data = data if not isinstance(data, dict) else self.response_data;
    }

    if self.on_message {
        self.on_message(data);
    }
}
