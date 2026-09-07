--
-- PostgreSQL database dump
--

\restrict raJAbOr4R97ED5Eppf9mHEyRPNYmU0X1ncn7wpbYwOmDRuPdhyx4ar9IofhIaay

-- Dumped from database version 15.17 (Debian 15.17-1.pgdg13+1)
-- Dumped by pg_dump version 15.17 (Debian 15.17-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: achievements_catalog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.achievements_catalog (
    id integer NOT NULL,
    achievement_name character varying(100),
    description text,
    required_xp integer,
    reward_xp integer,
    reward_tokens integer
);


ALTER TABLE public.achievements_catalog OWNER TO postgres;

--
-- Name: achievements_catalog_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.achievements_catalog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.achievements_catalog_id_seq OWNER TO postgres;

--
-- Name: achievements_catalog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.achievements_catalog_id_seq OWNED BY public.achievements_catalog.id;


--
-- Name: agent_conversations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_conversations (
    id integer NOT NULL,
    agent_name character varying(20),
    conversation_with character varying(20),
    message text,
    message_type character varying(20),
    xp_earned integer DEFAULT 0,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.agent_conversations OWNER TO postgres;

--
-- Name: agent_conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_conversations_id_seq OWNER TO postgres;

--
-- Name: agent_conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_conversations_id_seq OWNED BY public.agent_conversations.id;


--
-- Name: agent_errors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_errors (
    id integer NOT NULL,
    agent_name character varying(20),
    signal_id integer,
    error_category character varying(50),
    error_description text,
    root_cause text,
    severity integer DEFAULT 5,
    is_fixed boolean DEFAULT false,
    fixed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.agent_errors OWNER TO postgres;

--
-- Name: agent_errors_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_errors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_errors_id_seq OWNER TO postgres;

--
-- Name: agent_errors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_errors_id_seq OWNED BY public.agent_errors.id;


--
-- Name: agent_identities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_identities (
    id integer NOT NULL,
    agent_name character varying(20) NOT NULL,
    electronic_fingerprint character varying(128) NOT NULL,
    fingerprint_algorithm character varying(20) DEFAULT 'SHA3-256'::character varying,
    public_key text NOT NULL,
    private_key_encrypted text NOT NULL,
    certificate_serial character varying(64),
    certificate_issued_at timestamp without time zone DEFAULT now(),
    certificate_expires_at timestamp without time zone,
    is_revoked boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.agent_identities OWNER TO postgres;

--
-- Name: agent_identities_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_identities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_identities_id_seq OWNER TO postgres;

--
-- Name: agent_identities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_identities_id_seq OWNED BY public.agent_identities.id;


--
-- Name: agent_learning_progress; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_learning_progress (
    id integer NOT NULL,
    agent_name character varying(20),
    learning_date date DEFAULT CURRENT_DATE,
    topics_learned_today text[] DEFAULT '{}'::text[],
    lessons_received integer DEFAULT 0,
    xp_gained_today integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.agent_learning_progress OWNER TO postgres;

--
-- Name: agent_learning_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_learning_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_learning_progress_id_seq OWNER TO postgres;

--
-- Name: agent_learning_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_learning_progress_id_seq OWNED BY public.agent_learning_progress.id;


--
-- Name: agent_learning_topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_learning_topics (
    id integer NOT NULL,
    agent_name character varying(20),
    topic_name character varying(100),
    content text,
    source_agent character varying(20),
    is_learned boolean DEFAULT false,
    learned_at timestamp without time zone,
    xp_gained integer DEFAULT 0
);


ALTER TABLE public.agent_learning_topics OWNER TO postgres;

--
-- Name: agent_learning_topics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_learning_topics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_learning_topics_id_seq OWNER TO postgres;

--
-- Name: agent_learning_topics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_learning_topics_id_seq OWNED BY public.agent_learning_topics.id;


--
-- Name: agent_rewards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_rewards (
    id integer NOT NULL,
    agent_name character varying(20),
    reward_type character varying(30),
    reward_name character varying(100),
    reward_value integer,
    unlocked_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.agent_rewards OWNER TO postgres;

--
-- Name: agent_rewards_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_rewards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_rewards_id_seq OWNER TO postgres;

--
-- Name: agent_rewards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_rewards_id_seq OWNED BY public.agent_rewards.id;


--
-- Name: agent_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_sessions (
    id integer NOT NULL,
    agent_name character varying(20),
    session_token character varying(256) NOT NULL,
    started_at timestamp without time zone DEFAULT now(),
    expires_at timestamp without time zone,
    last_activity timestamp without time zone,
    is_active boolean DEFAULT true,
    terminated_reason text
);


ALTER TABLE public.agent_sessions OWNER TO postgres;

--
-- Name: agent_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_sessions_id_seq OWNER TO postgres;

--
-- Name: agent_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_sessions_id_seq OWNED BY public.agent_sessions.id;


--
-- Name: agent_votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_votes (
    id integer NOT NULL,
    signal_id integer,
    agent_name character varying(20),
    vote character varying(4),
    confidence numeric(5,2),
    trust_weight_at_time numeric(5,4),
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.agent_votes OWNER TO postgres;

--
-- Name: agent_votes_full; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_votes_full (
    id integer NOT NULL,
    signal_id integer,
    agent_name character varying(20),
    vote character varying(4),
    confidence numeric(5,2),
    trust_weight_at_time numeric(5,4),
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.agent_votes_full OWNER TO postgres;

--
-- Name: agent_votes_full_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_votes_full_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_votes_full_id_seq OWNER TO postgres;

--
-- Name: agent_votes_full_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_votes_full_id_seq OWNED BY public.agent_votes_full.id;


--
-- Name: agent_votes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.agent_votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.agent_votes_id_seq OWNER TO postgres;

--
-- Name: agent_votes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.agent_votes_id_seq OWNED BY public.agent_votes.id;


--
-- Name: broadcast_queue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.broadcast_queue (
    id integer NOT NULL,
    topic character varying(200),
    content text,
    broadcast_by character varying(20),
    total_agents integer DEFAULT 5,
    delivered_count integer DEFAULT 0,
    status character varying(20) DEFAULT 'PENDING'::character varying,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.broadcast_queue OWNER TO postgres;

--
-- Name: broadcast_queue_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.broadcast_queue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.broadcast_queue_id_seq OWNER TO postgres;

--
-- Name: broadcast_queue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.broadcast_queue_id_seq OWNED BY public.broadcast_queue.id;


--
-- Name: collaboration_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.collaboration_metrics (
    id integer NOT NULL,
    signal_id integer,
    consensus_reached boolean,
    consensus_percentage numeric(5,2),
    teamwork_score numeric(5,2),
    zero_error_contribution boolean DEFAULT false,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.collaboration_metrics OWNER TO postgres;

--
-- Name: collaboration_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.collaboration_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.collaboration_metrics_id_seq OWNER TO postgres;

--
-- Name: collaboration_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.collaboration_metrics_id_seq OWNED BY public.collaboration_metrics.id;


--
-- Name: core_agents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.core_agents (
    id integer NOT NULL,
    agent_name character varying(20) NOT NULL,
    agent_type character varying(30),
    specialization character varying(50),
    xp_points integer DEFAULT 0,
    token_balance integer DEFAULT 1000,
    achievements_count integer DEFAULT 0,
    level integer DEFAULT 1,
    trust_weight numeric(5,4) DEFAULT 0.2000,
    total_votes integer DEFAULT 0,
    correct_votes integer DEFAULT 0,
    vote_accuracy numeric(5,2) DEFAULT 0,
    is_active boolean DEFAULT true,
    is_enrolled boolean DEFAULT false,
    enrollment_date timestamp without time zone,
    last_heartbeat timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.core_agents OWNER TO postgres;

--
-- Name: core_agents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.core_agents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.core_agents_id_seq OWNER TO postgres;

--
-- Name: core_agents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.core_agents_id_seq OWNED BY public.core_agents.id;


--
-- Name: gatekeeper_audit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gatekeeper_audit (
    id integer NOT NULL,
    signal_id integer,
    agent_name character varying(20),
    identity_passed boolean,
    logic_passed boolean,
    resource_passed boolean,
    gate_status character varying(30),
    block_reason text,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.gatekeeper_audit OWNER TO postgres;

--
-- Name: gatekeeper_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.gatekeeper_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gatekeeper_audit_id_seq OWNER TO postgres;

--
-- Name: gatekeeper_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.gatekeeper_audit_id_seq OWNED BY public.gatekeeper_audit.id;


--
-- Name: gatekeeper_full_audit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gatekeeper_full_audit (
    id integer NOT NULL,
    signal_id integer,
    agent_name character varying(20),
    pillar1_identity_passed boolean,
    pillar2_logic_passed boolean,
    pillar3_resource_passed boolean,
    gate_status character varying(30),
    block_reason text,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.gatekeeper_full_audit OWNER TO postgres;

--
-- Name: gatekeeper_full_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.gatekeeper_full_audit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gatekeeper_full_audit_id_seq OWNER TO postgres;

--
-- Name: gatekeeper_full_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.gatekeeper_full_audit_id_seq OWNED BY public.gatekeeper_full_audit.id;


--
-- Name: group_votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_votes (
    id integer NOT NULL,
    signal_id integer,
    buy_votes integer,
    sell_votes integer,
    hold_votes integer,
    buy_percent numeric(5,2),
    sell_percent numeric(5,2),
    hold_percent numeric(5,2),
    final_decision character varying(4),
    decision_confidence numeric(5,2),
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.group_votes OWNER TO postgres;

--
-- Name: group_votes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.group_votes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.group_votes_id_seq OWNER TO postgres;

--
-- Name: group_votes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.group_votes_id_seq OWNED BY public.group_votes.id;


--
-- Name: knowledge_exchange; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.knowledge_exchange (
    id integer NOT NULL,
    from_agent character varying(20),
    to_agent character varying(20),
    knowledge_type character varying(50),
    topic character varying(200),
    content text,
    xp_reward integer DEFAULT 10,
    token_reward integer DEFAULT 5,
    is_broadcast boolean DEFAULT false,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.knowledge_exchange OWNER TO postgres;

--
-- Name: knowledge_exchange_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.knowledge_exchange_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.knowledge_exchange_id_seq OWNER TO postgres;

--
-- Name: knowledge_exchange_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.knowledge_exchange_id_seq OWNED BY public.knowledge_exchange.id;


--
-- Name: ml_training_cycles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ml_training_cycles (
    id integer NOT NULL,
    cycle_number integer,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    pre_training_accuracy numeric(5,2),
    post_training_accuracy numeric(5,2),
    agents_trained text[],
    status character varying(20),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ml_training_cycles OWNER TO postgres;

--
-- Name: ml_training_cycles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ml_training_cycles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ml_training_cycles_id_seq OWNER TO postgres;

--
-- Name: ml_training_cycles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ml_training_cycles_id_seq OWNED BY public.ml_training_cycles.id;


--
-- Name: platform_savepoints; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.platform_savepoints (
    id integer NOT NULL,
    checkpoint_time timestamp without time zone DEFAULT now(),
    agents_snapshot jsonb,
    total_xp integer,
    total_tokens integer
);


ALTER TABLE public.platform_savepoints OWNER TO postgres;

--
-- Name: platform_savepoints_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.platform_savepoints_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.platform_savepoints_id_seq OWNER TO postgres;

--
-- Name: platform_savepoints_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.platform_savepoints_id_seq OWNED BY public.platform_savepoints.id;


--
-- Name: rl_experience_buffer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rl_experience_buffer (
    id integer NOT NULL,
    agent_name character varying(20),
    "timestamp" timestamp with time zone NOT NULL,
    state_features jsonb NOT NULL,
    action character varying(4),
    reward numeric(10,4),
    xp_change integer,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.rl_experience_buffer OWNER TO postgres;

--
-- Name: rl_experience_buffer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.rl_experience_buffer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rl_experience_buffer_id_seq OWNER TO postgres;

--
-- Name: rl_experience_buffer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.rl_experience_buffer_id_seq OWNED BY public.rl_experience_buffer.id;


--
-- Name: security_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.security_events (
    id integer NOT NULL,
    event_type character varying(50),
    agent_name character varying(20),
    error_message text,
    severity integer DEFAULT 5,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.security_events OWNER TO postgres;

--
-- Name: security_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.security_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.security_events_id_seq OWNER TO postgres;

--
-- Name: security_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.security_events_id_seq OWNED BY public.security_events.id;


--
-- Name: signed_actions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.signed_actions (
    id integer NOT NULL,
    agent_name character varying(20),
    action_type character varying(50),
    action_id integer,
    action_data text,
    action_hash character varying(128),
    agent_signature text,
    verification_result boolean,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.signed_actions OWNER TO postgres;

--
-- Name: signed_actions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.signed_actions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.signed_actions_id_seq OWNER TO postgres;

--
-- Name: signed_actions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.signed_actions_id_seq OWNED BY public.signed_actions.id;


--
-- Name: smi_5min_candles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.smi_5min_candles (
    id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    open numeric(10,2),
    high numeric(10,2),
    low numeric(10,2),
    close numeric(10,2),
    volume integer
);


ALTER TABLE public.smi_5min_candles OWNER TO postgres;

--
-- Name: smi_5min_candles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.smi_5min_candles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smi_5min_candles_id_seq OWNER TO postgres;

--
-- Name: smi_5min_candles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.smi_5min_candles_id_seq OWNED BY public.smi_5min_candles.id;


--
-- Name: smi_features; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.smi_features (
    id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    z_score_20 numeric(8,4),
    z_score_50 numeric(8,4),
    rsi_14 numeric(8,4),
    rsi_slope_5 numeric(8,4),
    trend_strength numeric(8,4),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.smi_features OWNER TO postgres;

--
-- Name: smi_features_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.smi_features_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.smi_features_id_seq OWNER TO postgres;

--
-- Name: smi_features_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.smi_features_id_seq OWNED BY public.smi_features.id;


--
-- Name: supervisor_decisions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.supervisor_decisions (
    id integer NOT NULL,
    signal_id integer,
    final_decision character varying(4),
    decision_confidence numeric(5,2),
    consensus_achieved boolean,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.supervisor_decisions OWNER TO postgres;

--
-- Name: supervisor_decisions_full; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.supervisor_decisions_full (
    id integer NOT NULL,
    signal_id integer,
    total_buy_votes integer,
    total_sell_votes integer,
    total_hold_votes integer,
    buy_percentage numeric(5,2),
    sell_percentage numeric(5,2),
    hold_percentage numeric(5,2),
    final_decision character varying(4),
    decision_confidence numeric(5,2),
    consensus_achieved boolean,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.supervisor_decisions_full OWNER TO postgres;

--
-- Name: supervisor_decisions_full_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.supervisor_decisions_full_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.supervisor_decisions_full_id_seq OWNER TO postgres;

--
-- Name: supervisor_decisions_full_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.supervisor_decisions_full_id_seq OWNED BY public.supervisor_decisions_full.id;


--
-- Name: supervisor_decisions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.supervisor_decisions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.supervisor_decisions_id_seq OWNER TO postgres;

--
-- Name: supervisor_decisions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.supervisor_decisions_id_seq OWNED BY public.supervisor_decisions.id;


--
-- Name: supervisor_vote_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.supervisor_vote_records (
    id integer NOT NULL,
    signal_id integer,
    agent_name character varying(20),
    vote_cast character varying(4),
    confidence numeric(5,2),
    was_correct boolean,
    error_type character varying(50),
    xp_gained integer DEFAULT 0,
    xp_lost integer DEFAULT 0,
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.supervisor_vote_records OWNER TO postgres;

--
-- Name: supervisor_vote_records_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.supervisor_vote_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.supervisor_vote_records_id_seq OWNER TO postgres;

--
-- Name: supervisor_vote_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.supervisor_vote_records_id_seq OWNED BY public.supervisor_vote_records.id;


--
-- Name: telegram_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.telegram_metrics (
    id integer NOT NULL,
    date date DEFAULT CURRENT_DATE,
    total_messages_received integer DEFAULT 0,
    strong_signals integer DEFAULT 0,
    weak_signals integer DEFAULT 0,
    avg_confidence numeric(5,2) DEFAULT 0,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.telegram_metrics OWNER TO postgres;

--
-- Name: telegram_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.telegram_metrics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.telegram_metrics_id_seq OWNER TO postgres;

--
-- Name: telegram_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.telegram_metrics_id_seq OWNED BY public.telegram_metrics.id;


--
-- Name: telegram_signals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.telegram_signals (
    id integer NOT NULL,
    message_id bigint,
    chat_id bigint,
    asset_type character varying(20),
    current_price numeric(12,4),
    confidence_percent numeric(5,2),
    signal_strength character varying(20),
    data_source character varying(20),
    raw_message text,
    received_at timestamp without time zone DEFAULT now(),
    total_processing_ms integer,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.telegram_signals OWNER TO postgres;

--
-- Name: telegram_signals_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.telegram_signals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.telegram_signals_id_seq OWNER TO postgres;

--
-- Name: telegram_signals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.telegram_signals_id_seq OWNED BY public.telegram_signals.id;


--
-- Name: zero_error_milestones; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.zero_error_milestones (
    id integer NOT NULL,
    milestone_name character varying(100),
    achieved_at timestamp without time zone,
    consecutive_correct_trades integer,
    achieving_agents text[],
    is_active boolean DEFAULT true
);


ALTER TABLE public.zero_error_milestones OWNER TO postgres;

--
-- Name: zero_error_milestones_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.zero_error_milestones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.zero_error_milestones_id_seq OWNER TO postgres;

--
-- Name: zero_error_milestones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.zero_error_milestones_id_seq OWNED BY public.zero_error_milestones.id;


--
-- Name: achievements_catalog id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.achievements_catalog ALTER COLUMN id SET DEFAULT nextval('public.achievements_catalog_id_seq'::regclass);


--
-- Name: agent_conversations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_conversations ALTER COLUMN id SET DEFAULT nextval('public.agent_conversations_id_seq'::regclass);


--
-- Name: agent_errors id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_errors ALTER COLUMN id SET DEFAULT nextval('public.agent_errors_id_seq'::regclass);


--
-- Name: agent_identities id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_identities ALTER COLUMN id SET DEFAULT nextval('public.agent_identities_id_seq'::regclass);


--
-- Name: agent_learning_progress id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_learning_progress ALTER COLUMN id SET DEFAULT nextval('public.agent_learning_progress_id_seq'::regclass);


--
-- Name: agent_learning_topics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_learning_topics ALTER COLUMN id SET DEFAULT nextval('public.agent_learning_topics_id_seq'::regclass);


--
-- Name: agent_rewards id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_rewards ALTER COLUMN id SET DEFAULT nextval('public.agent_rewards_id_seq'::regclass);


--
-- Name: agent_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_sessions ALTER COLUMN id SET DEFAULT nextval('public.agent_sessions_id_seq'::regclass);


--
-- Name: agent_votes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_votes ALTER COLUMN id SET DEFAULT nextval('public.agent_votes_id_seq'::regclass);


--
-- Name: agent_votes_full id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_votes_full ALTER COLUMN id SET DEFAULT nextval('public.agent_votes_full_id_seq'::regclass);


--
-- Name: broadcast_queue id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.broadcast_queue ALTER COLUMN id SET DEFAULT nextval('public.broadcast_queue_id_seq'::regclass);


--
-- Name: collaboration_metrics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.collaboration_metrics ALTER COLUMN id SET DEFAULT nextval('public.collaboration_metrics_id_seq'::regclass);


--
-- Name: core_agents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_agents ALTER COLUMN id SET DEFAULT nextval('public.core_agents_id_seq'::regclass);


--
-- Name: gatekeeper_audit id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gatekeeper_audit ALTER COLUMN id SET DEFAULT nextval('public.gatekeeper_audit_id_seq'::regclass);


--
-- Name: gatekeeper_full_audit id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gatekeeper_full_audit ALTER COLUMN id SET DEFAULT nextval('public.gatekeeper_full_audit_id_seq'::regclass);


--
-- Name: group_votes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_votes ALTER COLUMN id SET DEFAULT nextval('public.group_votes_id_seq'::regclass);


--
-- Name: knowledge_exchange id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_exchange ALTER COLUMN id SET DEFAULT nextval('public.knowledge_exchange_id_seq'::regclass);


--
-- Name: ml_training_cycles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ml_training_cycles ALTER COLUMN id SET DEFAULT nextval('public.ml_training_cycles_id_seq'::regclass);


--
-- Name: platform_savepoints id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.platform_savepoints ALTER COLUMN id SET DEFAULT nextval('public.platform_savepoints_id_seq'::regclass);


--
-- Name: rl_experience_buffer id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rl_experience_buffer ALTER COLUMN id SET DEFAULT nextval('public.rl_experience_buffer_id_seq'::regclass);


--
-- Name: security_events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.security_events ALTER COLUMN id SET DEFAULT nextval('public.security_events_id_seq'::regclass);


--
-- Name: signed_actions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.signed_actions ALTER COLUMN id SET DEFAULT nextval('public.signed_actions_id_seq'::regclass);


--
-- Name: smi_5min_candles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.smi_5min_candles ALTER COLUMN id SET DEFAULT nextval('public.smi_5min_candles_id_seq'::regclass);


--
-- Name: smi_features id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.smi_features ALTER COLUMN id SET DEFAULT nextval('public.smi_features_id_seq'::regclass);


--
-- Name: supervisor_decisions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_decisions ALTER COLUMN id SET DEFAULT nextval('public.supervisor_decisions_id_seq'::regclass);


--
-- Name: supervisor_decisions_full id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_decisions_full ALTER COLUMN id SET DEFAULT nextval('public.supervisor_decisions_full_id_seq'::regclass);


--
-- Name: supervisor_vote_records id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_vote_records ALTER COLUMN id SET DEFAULT nextval('public.supervisor_vote_records_id_seq'::regclass);


--
-- Name: telegram_metrics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telegram_metrics ALTER COLUMN id SET DEFAULT nextval('public.telegram_metrics_id_seq'::regclass);


--
-- Name: telegram_signals id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telegram_signals ALTER COLUMN id SET DEFAULT nextval('public.telegram_signals_id_seq'::regclass);


--
-- Name: zero_error_milestones id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.zero_error_milestones ALTER COLUMN id SET DEFAULT nextval('public.zero_error_milestones_id_seq'::regclass);


--
-- Data for Name: achievements_catalog; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.achievements_catalog (id, achievement_name, description, required_xp, reward_xp, reward_tokens) FROM stdin;
1	Novice Trader	Complete first 10 trades	0	50	100
2	Seasoned Pro	Reach 1,000 XP	1000	200	500
3	Master Trader	Reach 5,000 XP	5000	500	1000
\.


--
-- Data for Name: agent_conversations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_conversations (id, agent_name, conversation_with, message, message_type, xp_earned, "timestamp") FROM stdin;
\.


--
-- Data for Name: agent_errors; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_errors (id, agent_name, signal_id, error_category, error_description, root_cause, severity, is_fixed, fixed_at, created_at) FROM stdin;
\.


--
-- Data for Name: agent_identities; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_identities (id, agent_name, electronic_fingerprint, fingerprint_algorithm, public_key, private_key_encrypted, certificate_serial, certificate_issued_at, certificate_expires_at, is_revoked, created_at) FROM stdin;
\.


--
-- Data for Name: agent_learning_progress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_learning_progress (id, agent_name, learning_date, topics_learned_today, lessons_received, xp_gained_today, created_at) FROM stdin;
\.


--
-- Data for Name: agent_learning_topics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_learning_topics (id, agent_name, topic_name, content, source_agent, is_learned, learned_at, xp_gained) FROM stdin;
\.


--
-- Data for Name: agent_rewards; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_rewards (id, agent_name, reward_type, reward_name, reward_value, unlocked_at) FROM stdin;
\.


--
-- Data for Name: agent_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_sessions (id, agent_name, session_token, started_at, expires_at, last_activity, is_active, terminated_reason) FROM stdin;
\.


--
-- Data for Name: agent_votes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_votes (id, signal_id, agent_name, vote, confidence, trust_weight_at_time, "timestamp") FROM stdin;
\.


--
-- Data for Name: agent_votes_full; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.agent_votes_full (id, signal_id, agent_name, vote, confidence, trust_weight_at_time, "timestamp") FROM stdin;
\.


--
-- Data for Name: broadcast_queue; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.broadcast_queue (id, topic, content, broadcast_by, total_agents, delivered_count, status, created_at) FROM stdin;
\.


--
-- Data for Name: collaboration_metrics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.collaboration_metrics (id, signal_id, consensus_reached, consensus_percentage, teamwork_score, zero_error_contribution, "timestamp") FROM stdin;
\.


--
-- Data for Name: core_agents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.core_agents (id, agent_name, agent_type, specialization, xp_points, token_balance, achievements_count, level, trust_weight, total_votes, correct_votes, vote_accuracy, is_active, is_enrolled, enrollment_date, last_heartbeat, created_at, updated_at) FROM stdin;
1	Agent_A	Trend Follower	Moving Average Crossovers	0	1000	0	1	0.2000	0	0	0.00	t	t	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185
2	Agent_B	Mean Reversion	RSI & Bollinger Bands	0	1000	0	1	0.2000	0	0	0.00	t	t	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185
3	Agent_C	Momentum	Price Rate of Change	0	1000	0	1	0.2000	0	0	0.00	t	t	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185
4	Agent_D	Volatility	ATR & Historical Vol	0	1000	0	1	0.2000	0	0	0.00	t	t	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185
5	Agent_E	Microstructure	Order Flow & Volume	0	1000	0	1	0.2000	0	0	0.00	t	t	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185	2026-04-07 20:33:44.710185
\.


--
-- Data for Name: gatekeeper_audit; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.gatekeeper_audit (id, signal_id, agent_name, identity_passed, logic_passed, resource_passed, gate_status, block_reason, "timestamp") FROM stdin;
\.


--
-- Data for Name: gatekeeper_full_audit; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.gatekeeper_full_audit (id, signal_id, agent_name, pillar1_identity_passed, pillar2_logic_passed, pillar3_resource_passed, gate_status, block_reason, "timestamp") FROM stdin;
\.


--
-- Data for Name: group_votes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_votes (id, signal_id, buy_votes, sell_votes, hold_votes, buy_percent, sell_percent, hold_percent, final_decision, decision_confidence, "timestamp") FROM stdin;
\.


--
-- Data for Name: knowledge_exchange; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.knowledge_exchange (id, from_agent, to_agent, knowledge_type, topic, content, xp_reward, token_reward, is_broadcast, "timestamp") FROM stdin;
\.


--
-- Data for Name: ml_training_cycles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ml_training_cycles (id, cycle_number, started_at, completed_at, pre_training_accuracy, post_training_accuracy, agents_trained, status, created_at) FROM stdin;
\.


--
-- Data for Name: platform_savepoints; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.platform_savepoints (id, checkpoint_time, agents_snapshot, total_xp, total_tokens) FROM stdin;
\.


--
-- Data for Name: rl_experience_buffer; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rl_experience_buffer (id, agent_name, "timestamp", state_features, action, reward, xp_change, created_at) FROM stdin;
\.


--
-- Data for Name: security_events; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.security_events (id, event_type, agent_name, error_message, severity, "timestamp") FROM stdin;
\.


--
-- Data for Name: signed_actions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.signed_actions (id, agent_name, action_type, action_id, action_data, action_hash, agent_signature, verification_result, "timestamp") FROM stdin;
\.


--
-- Data for Name: smi_5min_candles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.smi_5min_candles (id, "timestamp", open, high, low, close, volume) FROM stdin;
\.


--
-- Data for Name: smi_features; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.smi_features (id, "timestamp", z_score_20, z_score_50, rsi_14, rsi_slope_5, trend_strength, created_at) FROM stdin;
\.


--
-- Data for Name: supervisor_decisions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.supervisor_decisions (id, signal_id, final_decision, decision_confidence, consensus_achieved, "timestamp") FROM stdin;
\.


--
-- Data for Name: supervisor_decisions_full; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.supervisor_decisions_full (id, signal_id, total_buy_votes, total_sell_votes, total_hold_votes, buy_percentage, sell_percentage, hold_percentage, final_decision, decision_confidence, consensus_achieved, "timestamp") FROM stdin;
\.


--
-- Data for Name: supervisor_vote_records; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.supervisor_vote_records (id, signal_id, agent_name, vote_cast, confidence, was_correct, error_type, xp_gained, xp_lost, "timestamp") FROM stdin;
\.


--
-- Data for Name: telegram_metrics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.telegram_metrics (id, date, total_messages_received, strong_signals, weak_signals, avg_confidence, created_at) FROM stdin;
\.


--
-- Data for Name: telegram_signals; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.telegram_signals (id, message_id, chat_id, asset_type, current_price, confidence_percent, signal_strength, data_source, raw_message, received_at, total_processing_ms, created_at) FROM stdin;
\.


--
-- Data for Name: zero_error_milestones; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.zero_error_milestones (id, milestone_name, achieved_at, consecutive_correct_trades, achieving_agents, is_active) FROM stdin;
\.


--
-- Name: achievements_catalog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.achievements_catalog_id_seq', 3, true);


--
-- Name: agent_conversations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_conversations_id_seq', 1, false);


--
-- Name: agent_errors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_errors_id_seq', 1, false);


--
-- Name: agent_identities_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_identities_id_seq', 1, false);


--
-- Name: agent_learning_progress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_learning_progress_id_seq', 1, false);


--
-- Name: agent_learning_topics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_learning_topics_id_seq', 1, false);


--
-- Name: agent_rewards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_rewards_id_seq', 1, false);


--
-- Name: agent_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_sessions_id_seq', 1, false);


--
-- Name: agent_votes_full_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_votes_full_id_seq', 1, false);


--
-- Name: agent_votes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.agent_votes_id_seq', 1, false);


--
-- Name: broadcast_queue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.broadcast_queue_id_seq', 1, false);


--
-- Name: collaboration_metrics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.collaboration_metrics_id_seq', 1, false);


--
-- Name: core_agents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.core_agents_id_seq', 6, true);


--
-- Name: gatekeeper_audit_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.gatekeeper_audit_id_seq', 1, false);


--
-- Name: gatekeeper_full_audit_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.gatekeeper_full_audit_id_seq', 1, false);


--
-- Name: group_votes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.group_votes_id_seq', 1, false);


--
-- Name: knowledge_exchange_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.knowledge_exchange_id_seq', 1, false);


--
-- Name: ml_training_cycles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ml_training_cycles_id_seq', 1, false);


--
-- Name: platform_savepoints_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.platform_savepoints_id_seq', 1, false);


--
-- Name: rl_experience_buffer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.rl_experience_buffer_id_seq', 1, false);


--
-- Name: security_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.security_events_id_seq', 1, false);


--
-- Name: signed_actions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.signed_actions_id_seq', 1, false);


--
-- Name: smi_5min_candles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.smi_5min_candles_id_seq', 1, false);


--
-- Name: smi_features_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.smi_features_id_seq', 1, false);


--
-- Name: supervisor_decisions_full_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.supervisor_decisions_full_id_seq', 1, false);


--
-- Name: supervisor_decisions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.supervisor_decisions_id_seq', 1, false);


--
-- Name: supervisor_vote_records_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.supervisor_vote_records_id_seq', 1, false);


--
-- Name: telegram_metrics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.telegram_metrics_id_seq', 1, false);


--
-- Name: telegram_signals_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.telegram_signals_id_seq', 1, false);


--
-- Name: zero_error_milestones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.zero_error_milestones_id_seq', 1, false);


--
-- Name: achievements_catalog achievements_catalog_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.achievements_catalog
    ADD CONSTRAINT achievements_catalog_pkey PRIMARY KEY (id);


--
-- Name: agent_conversations agent_conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_conversations
    ADD CONSTRAINT agent_conversations_pkey PRIMARY KEY (id);


--
-- Name: agent_errors agent_errors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_errors
    ADD CONSTRAINT agent_errors_pkey PRIMARY KEY (id);


--
-- Name: agent_identities agent_identities_agent_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_identities
    ADD CONSTRAINT agent_identities_agent_name_key UNIQUE (agent_name);


--
-- Name: agent_identities agent_identities_certificate_serial_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_identities
    ADD CONSTRAINT agent_identities_certificate_serial_key UNIQUE (certificate_serial);


--
-- Name: agent_identities agent_identities_electronic_fingerprint_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_identities
    ADD CONSTRAINT agent_identities_electronic_fingerprint_key UNIQUE (electronic_fingerprint);


--
-- Name: agent_identities agent_identities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_identities
    ADD CONSTRAINT agent_identities_pkey PRIMARY KEY (id);


--
-- Name: agent_learning_progress agent_learning_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_learning_progress
    ADD CONSTRAINT agent_learning_progress_pkey PRIMARY KEY (id);


--
-- Name: agent_learning_topics agent_learning_topics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_learning_topics
    ADD CONSTRAINT agent_learning_topics_pkey PRIMARY KEY (id);


--
-- Name: agent_rewards agent_rewards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_rewards
    ADD CONSTRAINT agent_rewards_pkey PRIMARY KEY (id);


--
-- Name: agent_sessions agent_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_sessions
    ADD CONSTRAINT agent_sessions_pkey PRIMARY KEY (id);


--
-- Name: agent_sessions agent_sessions_session_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_sessions
    ADD CONSTRAINT agent_sessions_session_token_key UNIQUE (session_token);


--
-- Name: agent_votes_full agent_votes_full_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_votes_full
    ADD CONSTRAINT agent_votes_full_pkey PRIMARY KEY (id);


--
-- Name: agent_votes agent_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_votes
    ADD CONSTRAINT agent_votes_pkey PRIMARY KEY (id);


--
-- Name: broadcast_queue broadcast_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.broadcast_queue
    ADD CONSTRAINT broadcast_queue_pkey PRIMARY KEY (id);


--
-- Name: collaboration_metrics collaboration_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.collaboration_metrics
    ADD CONSTRAINT collaboration_metrics_pkey PRIMARY KEY (id);


--
-- Name: core_agents core_agents_agent_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_agents
    ADD CONSTRAINT core_agents_agent_name_key UNIQUE (agent_name);


--
-- Name: core_agents core_agents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.core_agents
    ADD CONSTRAINT core_agents_pkey PRIMARY KEY (id);


--
-- Name: gatekeeper_audit gatekeeper_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gatekeeper_audit
    ADD CONSTRAINT gatekeeper_audit_pkey PRIMARY KEY (id);


--
-- Name: gatekeeper_full_audit gatekeeper_full_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gatekeeper_full_audit
    ADD CONSTRAINT gatekeeper_full_audit_pkey PRIMARY KEY (id);


--
-- Name: group_votes group_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_votes
    ADD CONSTRAINT group_votes_pkey PRIMARY KEY (id);


--
-- Name: knowledge_exchange knowledge_exchange_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.knowledge_exchange
    ADD CONSTRAINT knowledge_exchange_pkey PRIMARY KEY (id);


--
-- Name: ml_training_cycles ml_training_cycles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ml_training_cycles
    ADD CONSTRAINT ml_training_cycles_pkey PRIMARY KEY (id);


--
-- Name: platform_savepoints platform_savepoints_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.platform_savepoints
    ADD CONSTRAINT platform_savepoints_pkey PRIMARY KEY (id);


--
-- Name: rl_experience_buffer rl_experience_buffer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rl_experience_buffer
    ADD CONSTRAINT rl_experience_buffer_pkey PRIMARY KEY (id);


--
-- Name: security_events security_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.security_events
    ADD CONSTRAINT security_events_pkey PRIMARY KEY (id);


--
-- Name: signed_actions signed_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.signed_actions
    ADD CONSTRAINT signed_actions_pkey PRIMARY KEY (id);


--
-- Name: smi_5min_candles smi_5min_candles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.smi_5min_candles
    ADD CONSTRAINT smi_5min_candles_pkey PRIMARY KEY (id);


--
-- Name: smi_5min_candles smi_5min_candles_timestamp_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.smi_5min_candles
    ADD CONSTRAINT smi_5min_candles_timestamp_key UNIQUE ("timestamp");


--
-- Name: smi_features smi_features_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.smi_features
    ADD CONSTRAINT smi_features_pkey PRIMARY KEY (id);


--
-- Name: supervisor_decisions_full supervisor_decisions_full_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_decisions_full
    ADD CONSTRAINT supervisor_decisions_full_pkey PRIMARY KEY (id);


--
-- Name: supervisor_decisions supervisor_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_decisions
    ADD CONSTRAINT supervisor_decisions_pkey PRIMARY KEY (id);


--
-- Name: supervisor_vote_records supervisor_vote_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_vote_records
    ADD CONSTRAINT supervisor_vote_records_pkey PRIMARY KEY (id);


--
-- Name: telegram_metrics telegram_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telegram_metrics
    ADD CONSTRAINT telegram_metrics_pkey PRIMARY KEY (id);


--
-- Name: telegram_signals telegram_signals_message_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telegram_signals
    ADD CONSTRAINT telegram_signals_message_id_key UNIQUE (message_id);


--
-- Name: telegram_signals telegram_signals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.telegram_signals
    ADD CONSTRAINT telegram_signals_pkey PRIMARY KEY (id);


--
-- Name: zero_error_milestones zero_error_milestones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.zero_error_milestones
    ADD CONSTRAINT zero_error_milestones_pkey PRIMARY KEY (id);


--
-- Name: agent_errors agent_errors_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_errors
    ADD CONSTRAINT agent_errors_agent_name_fkey FOREIGN KEY (agent_name) REFERENCES public.core_agents(agent_name);


--
-- Name: agent_errors agent_errors_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_errors
    ADD CONSTRAINT agent_errors_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- Name: agent_identities agent_identities_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_identities
    ADD CONSTRAINT agent_identities_agent_name_fkey FOREIGN KEY (agent_name) REFERENCES public.core_agents(agent_name);


--
-- Name: agent_learning_progress agent_learning_progress_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_learning_progress
    ADD CONSTRAINT agent_learning_progress_agent_name_fkey FOREIGN KEY (agent_name) REFERENCES public.core_agents(agent_name);


--
-- Name: agent_sessions agent_sessions_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_sessions
    ADD CONSTRAINT agent_sessions_agent_name_fkey FOREIGN KEY (agent_name) REFERENCES public.agent_identities(agent_name);


--
-- Name: agent_votes agent_votes_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_votes
    ADD CONSTRAINT agent_votes_agent_name_fkey FOREIGN KEY (agent_name) REFERENCES public.core_agents(agent_name);


--
-- Name: agent_votes_full agent_votes_full_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_votes_full
    ADD CONSTRAINT agent_votes_full_agent_name_fkey FOREIGN KEY (agent_name) REFERENCES public.core_agents(agent_name);


--
-- Name: agent_votes_full agent_votes_full_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_votes_full
    ADD CONSTRAINT agent_votes_full_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- Name: agent_votes agent_votes_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_votes
    ADD CONSTRAINT agent_votes_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- Name: collaboration_metrics collaboration_metrics_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.collaboration_metrics
    ADD CONSTRAINT collaboration_metrics_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- Name: gatekeeper_audit gatekeeper_audit_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gatekeeper_audit
    ADD CONSTRAINT gatekeeper_audit_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- Name: gatekeeper_full_audit gatekeeper_full_audit_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gatekeeper_full_audit
    ADD CONSTRAINT gatekeeper_full_audit_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- Name: group_votes group_votes_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_votes
    ADD CONSTRAINT group_votes_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- Name: supervisor_decisions_full supervisor_decisions_full_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_decisions_full
    ADD CONSTRAINT supervisor_decisions_full_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- Name: supervisor_decisions supervisor_decisions_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_decisions
    ADD CONSTRAINT supervisor_decisions_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- Name: supervisor_vote_records supervisor_vote_records_agent_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_vote_records
    ADD CONSTRAINT supervisor_vote_records_agent_name_fkey FOREIGN KEY (agent_name) REFERENCES public.core_agents(agent_name);


--
-- Name: supervisor_vote_records supervisor_vote_records_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.supervisor_vote_records
    ADD CONSTRAINT supervisor_vote_records_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.telegram_signals(id);


--
-- PostgreSQL database dump complete
--

\unrestrict raJAbOr4R97ED5Eppf9mHEyRPNYmU0X1ncn7wpbYwOmDRuPdhyx4ar9IofhIaay

