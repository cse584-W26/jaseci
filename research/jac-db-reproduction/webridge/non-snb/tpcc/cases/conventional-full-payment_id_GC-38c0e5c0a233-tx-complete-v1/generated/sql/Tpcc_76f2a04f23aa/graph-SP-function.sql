DROP FUNCTION IF EXISTS c_decimal;
DELIMITER $$
CREATE FUNCTION c_decimal(i BIGINT, s INT) RETURNS DECIMAL(19, 5)
BEGIN
RETURN i / POWER(10, s);
END$$
DELIMITER ;

DROP FUNCTION IF EXISTS get_int_compact;
DELIMITER $$
CREATE FUNCTION get_int_compact(d CHAR(19)) RETURNS INT
BEGIN
RETURN CONVERT(REPLACE(d, '.', ''), SIGNED);
END$$
DELIMITER ;

DROP FUNCTION IF EXISTS get_scale;
DELIMITER $$
CREATE FUNCTION get_scale(d CHAR(19)) RETURNS INT
BEGIN
IF NOT POSITION('.' in d) THEN
RETURN 0;
END IF;
RETURN CHAR_LENGTH(d) - POSITION('.' in d);
END$$
DELIMITER ;

DROP FUNCTION IF EXISTS u_rshift;
DELIMITER $$
CREATE FUNCTION u_rshift(n BIGINT, s BIGINT) RETURNS BIGINT
BEGIN
IF n > 0 THEN
RETURN n >> s;
END IF;
RETURN (n >> s) + (2 << ~s);
END$$
DELIMITER ;

DROP FUNCTION IF EXISTS index_of;
DELIMITER $$
CREATE FUNCTION index_of(long_str CHAR(255), short_str CHAR(255)) RETURNS INT
BEGIN
RETURN POSITION(short_str IN long_str) - 1;
END$$
DELIMITER ;

DROP FUNCTION IF EXISTS last_index_of_char_from;
DELIMITER $$
CREATE FUNCTION last_index_of_char_from(long_str CHAR(255), ch INT, from_pos INT) RETURNS INT
BEGIN
DECLARE considered_long_str CHAR(255);
DECLARE reversed_considered_long_str CHAR(255);
SET considered_long_str = SUBSTRING(long_str, 1, 1 + from_pos);
SET reversed_considered_long_str = REVERSE(considered_long_str);
IF POSITION(CHAR(ch) IN reversed_considered_long_str) = 0 THEN
RETURN -1;
ELSE
RETURN LENGTH(considered_long_str) - POSITION(CHAR(CH) IN reversed_considered_long_str);
END IF;
END$$
DELIMITER ;


DROP FUNCTION IF EXISTS Convert_ext;
DELIMITER $$
CREATE FUNCTION Convert_ext(str CHAR(255)) RETURNS INT
BEGIN
IF STRCMP(str, "true") = 0 THEN
RETURN 1;
ELSE IF STRCMP(str, "false") = 0 THEN
RETURN 0;
END IF;
END IF;
RETURN (CONVERT(str, SIGNED));
END$$
DELIMITER ;