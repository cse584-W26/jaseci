CREATE SEQUENCE public."anchors_seq_seq" AS bigint INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1 NO CYCLE;

CREATE TABLE public."adj_knows" ("src" uuid NOT NULL, "dst" uuid NOT NULL);

CREATE TABLE public."anchors" ("id" uuid NOT NULL, "kind" text NOT NULL, "arch_type" text DEFAULT ''::text NOT NULL, "arch_module" text DEFAULT ''::text NOT NULL, "fingerprint" text DEFAULT ''::text NOT NULL, "root_id" uuid, "src" uuid, "dst" uuid, "undirected" boolean DEFAULT false NOT NULL, "props" jsonb DEFAULT '{}'::jsonb NOT NULL, "format_version" integer DEFAULT 1 NOT NULL, "updated_at" timestamp with time zone DEFAULT now() NOT NULL, "seq" bigint DEFAULT nextval('anchors_seq_seq'::regclass) NOT NULL, "src_type" text, "dst_type" text);

CREATE TABLE public."g_n_comment_d2a57d" ("id" uuid NOT NULL, "root_id" uuid, "acl_all" smallint DEFAULT '-1'::integer NOT NULL, "acl_spec" boolean DEFAULT false NOT NULL, "frag" text DEFAULT '[]'::text NOT NULL, "f_comment_id" jsonb, "f_creationdate" jsonb, "f_locationip" jsonb, "f_browserused" jsonb, "f_content" jsonb, "f_length" jsonb, "root_of_replyof" uuid, "dst_endpoint_hascreator" uuid);

CREATE TABLE public."g_n_forum_d2a57d" ("id" uuid NOT NULL, "root_id" uuid, "acl_all" smallint DEFAULT '-1'::integer NOT NULL, "acl_spec" boolean DEFAULT false NOT NULL, "frag" text DEFAULT '[]'::text NOT NULL, "f_forum_id" jsonb, "f_title" jsonb, "f_creationdate" jsonb);

CREATE TABLE public."g_n_person_d2a57d" ("id" uuid NOT NULL, "root_id" uuid, "acl_all" smallint DEFAULT '-1'::integer NOT NULL, "acl_spec" boolean DEFAULT false NOT NULL, "frag" text DEFAULT '[]'::text NOT NULL, "f_person_id" jsonb, "f_firstname" jsonb, "f_lastname" jsonb, "f_gender" jsonb, "f_birthday" jsonb, "f_creationdate" jsonb, "f_locationip" jsonb, "f_browserused" jsonb);

CREATE TABLE public."g_n_post_d2a57d" ("id" uuid NOT NULL, "root_id" uuid, "acl_all" smallint DEFAULT '-1'::integer NOT NULL, "acl_spec" boolean DEFAULT false NOT NULL, "frag" text DEFAULT '[]'::text NOT NULL, "f_post_id" jsonb, "f_imagefile" jsonb, "f_creationdate" jsonb, "f_locationip" jsonb, "f_browserused" jsonb, "f_language" jsonb, "f_content" jsonb, "f_length" jsonb, "dst_endpoint_hascreator" uuid);

CREATE TABLE public."graph_types" ("type_name" text NOT NULL, "ancestor" text NOT NULL);

CREATE TABLE public."identity_lookups" ("value_normalized" text NOT NULL, "user_id" text NOT NULL);

CREATE TABLE public."identity_users" ("user_id" text NOT NULL, "doc" jsonb NOT NULL);

CREATE TABLE public."jac_docs" ("collection" text NOT NULL, "id" text NOT NULL, "doc" jsonb NOT NULL);

CREATE TABLE public."jac_ep_violation" ("tbl" text NOT NULL, "edge_type" text NOT NULL, "src" uuid NOT NULL, "noticed_at" timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public."kv_state" ("key" text NOT NULL, "value" text NOT NULL, "expires_at" timestamp with time zone, "updated_at" timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public."quarantine" ("missing_id" uuid NOT NULL, "referrer_id" uuid, "kind" text NOT NULL, "created_at" timestamp with time zone DEFAULT now() NOT NULL);

CREATE TABLE public."sso_lookups" ("provider" text NOT NULL, "external_id" text NOT NULL, "user_id" text NOT NULL);

ALTER TABLE public."anchors" ADD CONSTRAINT "anchors_pkey" PRIMARY KEY (id);

ALTER TABLE public."graph_types" ADD CONSTRAINT "graph_types_pkey" PRIMARY KEY (type_name, ancestor);

ALTER TABLE public."kv_state" ADD CONSTRAINT "kv_state_pkey" PRIMARY KEY (key);

ALTER TABLE public."quarantine" ADD CONSTRAINT "quarantine_pkey" PRIMARY KEY (missing_id, kind);

ALTER TABLE public."identity_users" ADD CONSTRAINT "identity_users_pkey" PRIMARY KEY (user_id);

ALTER TABLE public."identity_lookups" ADD CONSTRAINT "identity_lookups_pkey" PRIMARY KEY (value_normalized);

ALTER TABLE public."sso_lookups" ADD CONSTRAINT "sso_lookups_pkey" PRIMARY KEY (provider, external_id);

ALTER TABLE public."jac_docs" ADD CONSTRAINT "jac_docs_pkey" PRIMARY KEY (collection, id);

ALTER TABLE public."adj_knows" ADD CONSTRAINT "adj_knows_pkey" PRIMARY KEY (src, dst);

ALTER TABLE public."jac_ep_violation" ADD CONSTRAINT "jac_ep_violation_pkey" PRIMARY KEY (tbl, edge_type, src);

ALTER TABLE public."g_n_person_d2a57d" ADD CONSTRAINT "g_n_person_d2a57d_pkey" PRIMARY KEY (id);

ALTER TABLE public."g_n_post_d2a57d" ADD CONSTRAINT "g_n_post_d2a57d_pkey" PRIMARY KEY (id);

ALTER TABLE public."g_n_comment_d2a57d" ADD CONSTRAINT "g_n_comment_d2a57d_pkey" PRIMARY KEY (id);

ALTER TABLE public."g_n_forum_d2a57d" ADD CONSTRAINT "g_n_forum_d2a57d_pkey" PRIMARY KEY (id);

ALTER SEQUENCE public.anchors_seq_seq OWNED BY public.anchors.seq;

CREATE INDEX idx_adj_containerof_post_dst ON public.anchors USING btree (dst) INCLUDE (src) WHERE ((arch_type = 'ContainerOf'::text) AND (src_type = 'Post'::text));

CREATE INDEX idx_adj_containerof_post_src ON public.anchors USING btree (src) INCLUDE (dst) WHERE ((arch_type = 'ContainerOf'::text) AND (dst_type = 'Post'::text));

CREATE INDEX idx_adj_hascreator_person_dst ON public.anchors USING btree (dst) INCLUDE (src) WHERE ((arch_type = 'HasCreator'::text) AND (src_type = 'Person'::text));

CREATE INDEX idx_adj_hascreator_person_src ON public.anchors USING btree (src) INCLUDE (dst) WHERE ((arch_type = 'HasCreator'::text) AND (dst_type = 'Person'::text));

CREATE INDEX idx_adj_knows_person_dst ON public.anchors USING btree (dst) INCLUDE (src) WHERE ((arch_type = 'Knows'::text) AND (src_type = 'Person'::text));

CREATE INDEX idx_adj_knows_person_src ON public.anchors USING btree (src) INCLUDE (dst) WHERE ((arch_type = 'Knows'::text) AND (dst_type = 'Person'::text));

CREATE INDEX idx_anchors_dst ON public.anchors USING btree (dst, arch_type) WHERE (dst IS NOT NULL);

CREATE INDEX idx_anchors_dst_typed ON public.anchors USING btree (dst, arch_type, src_type) INCLUDE (src) WHERE (dst IS NOT NULL);

CREATE INDEX idx_anchors_kind_type ON public.anchors USING btree (kind, arch_type);

CREATE INDEX idx_anchors_root ON public.anchors USING btree (root_id) WHERE (root_id IS NOT NULL);

CREATE INDEX idx_anchors_src ON public.anchors USING btree (src, arch_type) WHERE (src IS NOT NULL);

CREATE INDEX idx_anchors_src_typed ON public.anchors USING btree (src, arch_type, dst_type) INCLUDE (dst) WHERE (src IS NOT NULL);

CREATE INDEX g_n_comment_d2a57d_epo_hascreator_f_creationdate ON public.g_n_comment_d2a57d USING btree (dst_endpoint_hascreator, (((f_creationdate #>> '{}'::text[]))::bigint) DESC);

CREATE INDEX g_n_person_d2a57d_gval_f_firstname ON public.g_n_person_d2a57d USING btree (((f_firstname #>> '{}'::text[])));

CREATE INDEX g_n_person_d2a57d_gval_f_person_id ON public.g_n_person_d2a57d USING btree (((f_person_id #>> '{}'::text[])));

CREATE INDEX g_n_post_d2a57d_epo_hascreator_f_creationdate ON public.g_n_post_d2a57d USING btree (dst_endpoint_hascreator, (((f_creationdate #>> '{}'::text[]))::bigint) DESC);

CREATE INDEX idx_identity_lookups_user ON public.identity_lookups USING btree (user_id);

CREATE OR REPLACE FUNCTION public.adj_knows_sync()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN IF TG_OP = 'DELETE' THEN DELETE FROM adj_knows a WHERE (a.src, a.dst) IN ((OLD.src, OLD.dst), (OLD.dst, OLD.src)) AND NOT EXISTS (SELECT 1 FROM anchors e WHERE e.kind = 'EdgeAnchor' AND e.arch_type = 'Knows' AND e.src_type = 'Person' AND e.dst_type = 'Person' AND e.src IS NOT NULL AND e.dst IS NOT NULL AND ((e.src = a.src AND e.dst = a.dst) OR (e.src = a.dst AND e.dst = a.src))); RETURN OLD; END IF; INSERT INTO adj_knows (src, dst) VALUES (NEW.src, NEW.dst), (NEW.dst, NEW.src) ON CONFLICT DO NOTHING; RETURN NEW; END $function$
;

CREATE OR REPLACE FUNCTION public.g_n_comment_d2a57d_epo_hascreator()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ DECLARE cur uuid; BEGIN IF to_regclass('g_n_comment_d2a57d') IS NULL THEN RETURN COALESCE(NEW, OLD); END IF; IF TG_OP <> 'INSERT' THEN UPDATE g_n_comment_d2a57d SET dst_endpoint_hascreator = NULL WHERE id = OLD.src AND dst_endpoint_hascreator = OLD.dst; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; END IF; SELECT dst_endpoint_hascreator INTO cur FROM g_n_comment_d2a57d WHERE id = NEW.src FOR UPDATE; IF cur IS NOT NULL AND cur <> NEW.dst THEN INSERT INTO jac_ep_violation (tbl, edge_type, src) VALUES ('g_n_comment_d2a57d', 'HasCreator', NEW.src) ON CONFLICT DO NOTHING; UPDATE g_n_comment_d2a57d SET dst_endpoint_hascreator = NULL WHERE id = NEW.src; RAISE WARNING 'jac: g_n_comment_d2a57d.dst_endpoint_hascreator cardinality violated at % - a second HasCreator edge appeared; endpoint column disabled for this mirror', NEW.src; RETURN NEW; END IF; INSERT INTO g_n_comment_d2a57d (id, dst_endpoint_hascreator) VALUES (NEW.src, NEW.dst) ON CONFLICT (id) DO UPDATE SET dst_endpoint_hascreator = EXCLUDED.dst_endpoint_hascreator; RETURN NEW; END $function$
;

CREATE OR REPLACE FUNCTION public.g_n_comment_d2a57d_root_replyof()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ DECLARE r uuid; BEGIN IF to_regclass('g_n_comment_d2a57d') IS NULL THEN RETURN COALESCE(NEW, OLD); END IF; IF TG_OP = 'DELETE' OR (TG_OP = 'UPDATE' AND (OLD.src IS DISTINCT FROM NEW.src OR OLD.dst IS DISTINCT FROM NEW.dst)) THEN INSERT INTO jac_ep_violation (tbl, edge_type, src) VALUES ('g_n_comment_d2a57d', 'ReplyOf', OLD.src) ON CONFLICT DO NOTHING; RAISE WARNING 'jac: g_n_comment_d2a57d.root_of_replyof chain edge mutated at % (%); root column disabled for this mirror', OLD.src, TG_OP; RETURN COALESCE(NEW, OLD); END IF; IF NEW.dst_type = 'Post' THEN r := NEW.dst; ELSE SELECT root_of_replyof INTO r FROM g_n_comment_d2a57d WHERE id = NEW.dst; END IF; IF r IS NULL THEN RETURN NEW; END IF; INSERT INTO g_n_comment_d2a57d (id, root_of_replyof) VALUES (NEW.src, r) ON CONFLICT (id) DO UPDATE SET root_of_replyof = EXCLUDED.root_of_replyof; RETURN NEW; END $function$
;

CREATE OR REPLACE FUNCTION public.g_n_comment_d2a57d_sync()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN IF TG_OP = 'DELETE' THEN DELETE FROM g_n_comment_d2a57d WHERE id = OLD.id; RETURN OLD; END IF; INSERT INTO g_n_comment_d2a57d (id, root_id, acl_all, acl_spec, frag, f_comment_id, f_creationdate, f_locationip, f_browserused, f_content, f_length) VALUES (NEW.id, NEW.root_id, CASE WHEN jsonb_typeof(NEW.props->'access'->'all') = 'number' THEN (NEW.props->'access'->>'all')::smallint ELSE -1 END, COALESCE(NEW.props->'access'->'roots'->'anchors', '{}'::jsonb) <> '{}'::jsonb, (COALESCE((SELECT jsonb_object_agg(k.key, k.value) FROM jsonb_each(COALESCE(NEW.props->'archetype', '{}'::jsonb)) k WHERE left(k.key, 2) <> '__'), '{}'::jsonb) || jsonb_build_object('_jac_type', NEW.arch_type, '_jac_id', replace(NEW.id::text, '-', ''), '_jac_archetype', 'node'))::text, NEW.props->'archetype'->'comment_id', NEW.props->'archetype'->'creationDate', NEW.props->'archetype'->'locationIP', NEW.props->'archetype'->'browserUsed', NEW.props->'archetype'->'content', NEW.props->'archetype'->'length') ON CONFLICT (id) DO UPDATE SET root_id = EXCLUDED.root_id, acl_all = EXCLUDED.acl_all, acl_spec = EXCLUDED.acl_spec, frag = EXCLUDED.frag, f_comment_id = EXCLUDED.f_comment_id, f_creationdate = EXCLUDED.f_creationdate, f_locationip = EXCLUDED.f_locationip, f_browserused = EXCLUDED.f_browserused, f_content = EXCLUDED.f_content, f_length = EXCLUDED.f_length; RETURN NEW; END $function$
;

CREATE OR REPLACE FUNCTION public.g_n_forum_d2a57d_sync()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN IF TG_OP = 'DELETE' THEN DELETE FROM g_n_forum_d2a57d WHERE id = OLD.id; RETURN OLD; END IF; INSERT INTO g_n_forum_d2a57d (id, root_id, acl_all, acl_spec, frag, f_forum_id, f_title, f_creationdate) VALUES (NEW.id, NEW.root_id, CASE WHEN jsonb_typeof(NEW.props->'access'->'all') = 'number' THEN (NEW.props->'access'->>'all')::smallint ELSE -1 END, COALESCE(NEW.props->'access'->'roots'->'anchors', '{}'::jsonb) <> '{}'::jsonb, (COALESCE((SELECT jsonb_object_agg(k.key, k.value) FROM jsonb_each(COALESCE(NEW.props->'archetype', '{}'::jsonb)) k WHERE left(k.key, 2) <> '__'), '{}'::jsonb) || jsonb_build_object('_jac_type', NEW.arch_type, '_jac_id', replace(NEW.id::text, '-', ''), '_jac_archetype', 'node'))::text, NEW.props->'archetype'->'forum_id', NEW.props->'archetype'->'title', NEW.props->'archetype'->'creationDate') ON CONFLICT (id) DO UPDATE SET root_id = EXCLUDED.root_id, acl_all = EXCLUDED.acl_all, acl_spec = EXCLUDED.acl_spec, frag = EXCLUDED.frag, f_forum_id = EXCLUDED.f_forum_id, f_title = EXCLUDED.f_title, f_creationdate = EXCLUDED.f_creationdate; RETURN NEW; END $function$
;

CREATE OR REPLACE FUNCTION public.g_n_person_d2a57d_sync()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN IF TG_OP = 'DELETE' THEN DELETE FROM g_n_person_d2a57d WHERE id = OLD.id; RETURN OLD; END IF; INSERT INTO g_n_person_d2a57d (id, root_id, acl_all, acl_spec, frag, f_person_id, f_firstname, f_lastname, f_gender, f_birthday, f_creationdate, f_locationip, f_browserused) VALUES (NEW.id, NEW.root_id, CASE WHEN jsonb_typeof(NEW.props->'access'->'all') = 'number' THEN (NEW.props->'access'->>'all')::smallint ELSE -1 END, COALESCE(NEW.props->'access'->'roots'->'anchors', '{}'::jsonb) <> '{}'::jsonb, (COALESCE((SELECT jsonb_object_agg(k.key, k.value) FROM jsonb_each(COALESCE(NEW.props->'archetype', '{}'::jsonb)) k WHERE left(k.key, 2) <> '__'), '{}'::jsonb) || jsonb_build_object('_jac_type', NEW.arch_type, '_jac_id', replace(NEW.id::text, '-', ''), '_jac_archetype', 'node'))::text, NEW.props->'archetype'->'person_id', NEW.props->'archetype'->'firstName', NEW.props->'archetype'->'lastName', NEW.props->'archetype'->'gender', NEW.props->'archetype'->'birthday', NEW.props->'archetype'->'creationDate', NEW.props->'archetype'->'locationIP', NEW.props->'archetype'->'browserUsed') ON CONFLICT (id) DO UPDATE SET root_id = EXCLUDED.root_id, acl_all = EXCLUDED.acl_all, acl_spec = EXCLUDED.acl_spec, frag = EXCLUDED.frag, f_person_id = EXCLUDED.f_person_id, f_firstname = EXCLUDED.f_firstname, f_lastname = EXCLUDED.f_lastname, f_gender = EXCLUDED.f_gender, f_birthday = EXCLUDED.f_birthday, f_creationdate = EXCLUDED.f_creationdate, f_locationip = EXCLUDED.f_locationip, f_browserused = EXCLUDED.f_browserused; RETURN NEW; END $function$
;

CREATE OR REPLACE FUNCTION public.g_n_post_d2a57d_epo_hascreator()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ DECLARE cur uuid; BEGIN IF to_regclass('g_n_post_d2a57d') IS NULL THEN RETURN COALESCE(NEW, OLD); END IF; IF TG_OP <> 'INSERT' THEN UPDATE g_n_post_d2a57d SET dst_endpoint_hascreator = NULL WHERE id = OLD.src AND dst_endpoint_hascreator = OLD.dst; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; END IF; SELECT dst_endpoint_hascreator INTO cur FROM g_n_post_d2a57d WHERE id = NEW.src FOR UPDATE; IF cur IS NOT NULL AND cur <> NEW.dst THEN INSERT INTO jac_ep_violation (tbl, edge_type, src) VALUES ('g_n_post_d2a57d', 'HasCreator', NEW.src) ON CONFLICT DO NOTHING; UPDATE g_n_post_d2a57d SET dst_endpoint_hascreator = NULL WHERE id = NEW.src; RAISE WARNING 'jac: g_n_post_d2a57d.dst_endpoint_hascreator cardinality violated at % - a second HasCreator edge appeared; endpoint column disabled for this mirror', NEW.src; RETURN NEW; END IF; INSERT INTO g_n_post_d2a57d (id, dst_endpoint_hascreator) VALUES (NEW.src, NEW.dst) ON CONFLICT (id) DO UPDATE SET dst_endpoint_hascreator = EXCLUDED.dst_endpoint_hascreator; RETURN NEW; END $function$
;

CREATE OR REPLACE FUNCTION public.g_n_post_d2a57d_sync()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$ BEGIN IF TG_OP = 'DELETE' THEN DELETE FROM g_n_post_d2a57d WHERE id = OLD.id; RETURN OLD; END IF; INSERT INTO g_n_post_d2a57d (id, root_id, acl_all, acl_spec, frag, f_post_id, f_imagefile, f_creationdate, f_locationip, f_browserused, f_language, f_content, f_length) VALUES (NEW.id, NEW.root_id, CASE WHEN jsonb_typeof(NEW.props->'access'->'all') = 'number' THEN (NEW.props->'access'->>'all')::smallint ELSE -1 END, COALESCE(NEW.props->'access'->'roots'->'anchors', '{}'::jsonb) <> '{}'::jsonb, (COALESCE((SELECT jsonb_object_agg(k.key, k.value) FROM jsonb_each(COALESCE(NEW.props->'archetype', '{}'::jsonb)) k WHERE left(k.key, 2) <> '__'), '{}'::jsonb) || jsonb_build_object('_jac_type', NEW.arch_type, '_jac_id', replace(NEW.id::text, '-', ''), '_jac_archetype', 'node'))::text, NEW.props->'archetype'->'post_id', NEW.props->'archetype'->'imageFile', NEW.props->'archetype'->'creationDate', NEW.props->'archetype'->'locationIP', NEW.props->'archetype'->'browserUsed', NEW.props->'archetype'->'language', NEW.props->'archetype'->'content', NEW.props->'archetype'->'length') ON CONFLICT (id) DO UPDATE SET root_id = EXCLUDED.root_id, acl_all = EXCLUDED.acl_all, acl_spec = EXCLUDED.acl_spec, frag = EXCLUDED.frag, f_post_id = EXCLUDED.f_post_id, f_imagefile = EXCLUDED.f_imagefile, f_creationdate = EXCLUDED.f_creationdate, f_locationip = EXCLUDED.f_locationip, f_browserused = EXCLUDED.f_browserused, f_language = EXCLUDED.f_language, f_content = EXCLUDED.f_content, f_length = EXCLUDED.f_length; RETURN NEW; END $function$
;

CREATE TRIGGER adj_knows_del AFTER DELETE ON anchors FOR EACH ROW WHEN (old.kind = 'EdgeAnchor'::text AND old.arch_type = 'Knows'::text AND old.src_type = 'Person'::text AND old.dst_type = 'Person'::text AND old.src IS NOT NULL AND old.dst IS NOT NULL) EXECUTE FUNCTION adj_knows_sync();

CREATE TRIGGER adj_knows_ins AFTER INSERT OR UPDATE ON anchors FOR EACH ROW WHEN (new.kind = 'EdgeAnchor'::text AND new.arch_type = 'Knows'::text AND new.src_type = 'Person'::text AND new.dst_type = 'Person'::text AND new.src IS NOT NULL AND new.dst IS NOT NULL) EXECUTE FUNCTION adj_knows_sync();

CREATE TRIGGER g_n_comment_d2a57d_del AFTER DELETE ON anchors FOR EACH ROW WHEN (old.kind = 'NodeAnchor'::text AND old.arch_type = 'Comment'::text) EXECUTE FUNCTION g_n_comment_d2a57d_sync();

CREATE TRIGGER g_n_comment_d2a57d_epo_hascreator_d AFTER DELETE ON anchors FOR EACH ROW WHEN (old.kind = 'EdgeAnchor'::text AND old.arch_type = 'HasCreator'::text AND old.src_type = 'Comment'::text) EXECUTE FUNCTION g_n_comment_d2a57d_epo_hascreator();

CREATE TRIGGER g_n_comment_d2a57d_epo_hascreator_iu AFTER INSERT OR UPDATE ON anchors FOR EACH ROW WHEN (new.kind = 'EdgeAnchor'::text AND new.arch_type = 'HasCreator'::text AND new.src_type = 'Comment'::text) EXECUTE FUNCTION g_n_comment_d2a57d_epo_hascreator();

CREATE TRIGGER g_n_comment_d2a57d_ins AFTER INSERT OR UPDATE ON anchors FOR EACH ROW WHEN (new.kind = 'NodeAnchor'::text AND new.arch_type = 'Comment'::text) EXECUTE FUNCTION g_n_comment_d2a57d_sync();

CREATE TRIGGER g_n_comment_d2a57d_root_replyof_d AFTER DELETE ON anchors FOR EACH ROW WHEN (old.kind = 'EdgeAnchor'::text AND old.arch_type = 'ReplyOf'::text AND old.src_type = 'Comment'::text) EXECUTE FUNCTION g_n_comment_d2a57d_root_replyof();

CREATE TRIGGER g_n_comment_d2a57d_root_replyof_iu AFTER INSERT OR UPDATE ON anchors FOR EACH ROW WHEN (new.kind = 'EdgeAnchor'::text AND new.arch_type = 'ReplyOf'::text AND new.src_type = 'Comment'::text) EXECUTE FUNCTION g_n_comment_d2a57d_root_replyof();

CREATE TRIGGER g_n_forum_d2a57d_del AFTER DELETE ON anchors FOR EACH ROW WHEN (old.kind = 'NodeAnchor'::text AND old.arch_type = 'Forum'::text) EXECUTE FUNCTION g_n_forum_d2a57d_sync();

CREATE TRIGGER g_n_forum_d2a57d_ins AFTER INSERT OR UPDATE ON anchors FOR EACH ROW WHEN (new.kind = 'NodeAnchor'::text AND new.arch_type = 'Forum'::text) EXECUTE FUNCTION g_n_forum_d2a57d_sync();

CREATE TRIGGER g_n_person_d2a57d_del AFTER DELETE ON anchors FOR EACH ROW WHEN (old.kind = 'NodeAnchor'::text AND old.arch_type = 'Person'::text) EXECUTE FUNCTION g_n_person_d2a57d_sync();

CREATE TRIGGER g_n_person_d2a57d_ins AFTER INSERT OR UPDATE ON anchors FOR EACH ROW WHEN (new.kind = 'NodeAnchor'::text AND new.arch_type = 'Person'::text) EXECUTE FUNCTION g_n_person_d2a57d_sync();

CREATE TRIGGER g_n_post_d2a57d_del AFTER DELETE ON anchors FOR EACH ROW WHEN (old.kind = 'NodeAnchor'::text AND old.arch_type = 'Post'::text) EXECUTE FUNCTION g_n_post_d2a57d_sync();

CREATE TRIGGER g_n_post_d2a57d_epo_hascreator_d AFTER DELETE ON anchors FOR EACH ROW WHEN (old.kind = 'EdgeAnchor'::text AND old.arch_type = 'HasCreator'::text AND old.src_type = 'Post'::text) EXECUTE FUNCTION g_n_post_d2a57d_epo_hascreator();

CREATE TRIGGER g_n_post_d2a57d_epo_hascreator_iu AFTER INSERT OR UPDATE ON anchors FOR EACH ROW WHEN (new.kind = 'EdgeAnchor'::text AND new.arch_type = 'HasCreator'::text AND new.src_type = 'Post'::text) EXECUTE FUNCTION g_n_post_d2a57d_epo_hascreator();

CREATE TRIGGER g_n_post_d2a57d_ins AFTER INSERT OR UPDATE ON anchors FOR EACH ROW WHEN (new.kind = 'NodeAnchor'::text AND new.arch_type = 'Post'::text) EXECUTE FUNCTION g_n_post_d2a57d_sync();
