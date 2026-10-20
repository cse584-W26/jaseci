SqlNo=1
SQLNode {
    sqlTemplate='SELECT m.id, m.arch_type, m.props, a.props, r.props , ra.props FROM jac_snb_message_mirror m LEFT JOIN jac_snb_person_mirror a ON a.id = m.creator_id LEFT JOIN jac_snb_message_mirror r ON r.id = m.root_of_replyof LEFT JOIN jac_snb_person_mirror ra ON ra.id = r.creator_id WHERE m.creator_id = ? ORDER BY m.creation_date DESC, m.tie_id DESC LIMIT 10',
    parameters={M_L_String__REQUEST_PARAM_person_jid:VARCHAR},
    retVals={m.id:VARCHAR, m.arch_type:VARCHAR, m.props:LONGTEXT, a.props:LONGTEXT, r.props:LONGTEXT, ra.props:LONGTEXT}
}

======================================================
