SqlNo=1
SQLNode {
    sqlTemplate='set autocommit=0',
    parameters={},
    retVals={}
}
SqlNo=2
SQLNode {
    sqlTemplate='SELECT w_name FROM warehouse WHERE w_id = ? FOR UPDATE',
    parameters={M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value:INTEGER},
    retVals={w_name:VARCHAR}
}
SqlNo=3
SQLNode {
    sqlTemplate='SELECT d_name FROM district WHERE d_w_id = ? AND d_id = ? FOR UPDATE',
    parameters={M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value:INTEGER, M_J_field_REQUEST_PARAM_d_id_java_lang_Long_value:INTEGER},
    retVals={d_name:VARCHAR}
}
SqlNo=4
SQLNode {
    sqlTemplate='SELECT c_id, c_credit, c_data FROM customer WHERE c_w_id = ? AND c_d_id = ? AND c_id = ? FOR UPDATE',
    parameters={M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value:INTEGER, M_J_field_REQUEST_PARAM_c_d_id_java_lang_Long_value:INTEGER, M_J_field_REQUEST_PARAM_c_id_java_lang_Long_value:INTEGER},
    retVals={c_id:INTEGER, c_credit:VARCHAR, c_data:VARCHAR}
}
SqlNo=5
SQLNode {
    sqlTemplate='UPDATE warehouse SET w_ytd = w_ytd + ? WHERE w_id = ?',
    parameters={M_D_field_REQUEST_PARAM_amount_java_lang_Double_value:DECIMAL, M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value:INTEGER},
    retVals={}
}
SqlNo=6
SQLNode {
    sqlTemplate='UPDATE district SET d_ytd = d_ytd + ? WHERE d_w_id = ? AND d_id = ?',
    parameters={M_D_field_REQUEST_PARAM_amount_java_lang_Double_value:DECIMAL, M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value:INTEGER, M_J_field_REQUEST_PARAM_d_id_java_lang_Long_value:INTEGER},
    retVals={}
}
SqlNo=7
SQLNode {
    sqlTemplate='UPDATE customer SET c_balance = c_balance - ?, c_ytd_payment = c_ytd_payment + ?, c_payment_cnt = c_payment_cnt + 1 WHERE c_w_id = ? AND c_d_id = ? AND c_id = ?',
    parameters={M_D_field_REQUEST_PARAM_amount_java_lang_Double_value:DECIMAL, M_D_field_REQUEST_PARAM_amount_java_lang_Double_value:DECIMAL, M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value:INTEGER, M_J_field_REQUEST_PARAM_c_d_id_java_lang_Long_value:INTEGER, (0 - (((((((0 - ((ASCII(CONVERT(SUBSTRING(RS_q4_r1_col1, 0 + 1, 1), CHAR)) + 16) & 31)) * 10) - ((ASCII(CONVERT(SUBSTRING(RS_q4_r1_col1, 1 + 1, 1), CHAR)) + 16) & 31)) * 10) - ((ASCII(CONVERT(SUBSTRING(RS_q4_r1_col1, 2 + 1, 1), CHAR)) + 16) & 31)) * 10) - ((ASCII(CONVERT(SUBSTRING(RS_q4_r1_col1, 3 + 1, 1), CHAR)) + 16) & 31))):INTEGER},
    retVals={}
}
SqlNo=8
SQLNode {
    sqlTemplate='INSERT INTO history (h_c_id, h_c_d_id, h_c_w_id, h_d_id, h_w_id , h_date, h_amount, h_data) VALUES (?, ?, ?, ?, ? , ?, ?, ?)',
    parameters={(0 - (((((((0 - ((ASCII(CONVERT(SUBSTRING(RS_q4_r1_col1, 0 + 1, 1), CHAR)) + 16) & 31)) * 10) - ((ASCII(CONVERT(SUBSTRING(RS_q4_r1_col1, 1 + 1, 1), CHAR)) + 16) & 31)) * 10) - ((ASCII(CONVERT(SUBSTRING(RS_q4_r1_col1, 2 + 1, 1), CHAR)) + 16) & 31)) * 10) - ((ASCII(CONVERT(SUBSTRING(RS_q4_r1_col1, 3 + 1, 1), CHAR)) + 16) & 31))):INTEGER, M_J_field_REQUEST_PARAM_c_d_id_java_lang_Long_value:INTEGER, M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value:INTEGER, M_J_field_REQUEST_PARAM_d_id_java_lang_Long_value:INTEGER, M_J_field_REQUEST_PARAM_w_id_java_lang_Long_value:INTEGER, M_L_String__REQUEST_PARAM_timestamp:VARCHAR, M_D_field_REQUEST_PARAM_amount_java_lang_Double_value:DECIMAL, CONCAT(CONCAT(CONCAT("", RS_q2_r1_col1), "    "), RS_q3_r1_col1):VARCHAR},
    retVals={}
}
SqlNo=9
SQLNode {
    sqlTemplate='set autocommit=1',
    parameters={},
    retVals={}
}

======================================================
