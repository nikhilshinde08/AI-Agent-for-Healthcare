--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5 (Ubuntu 17.5-1.pgdg22.04+1)
-- Dumped by pg_dump version 17.5 (Ubuntu 17.5-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: allergies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.allergies (
    "START" date,
    "STOP" date,
    "PATIENT_ID" character varying,
    "ENCOUNTER_ID" character varying,
    "ALLERGY_CODE" bigint,
    "ALLERGY_DESCRIPTION" character varying
);


--
-- Name: careplans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.careplans (
    "CAREPLAN_ID" character varying,
    "START" date,
    "STOP" date,
    "PATIENT_ID" character varying,
    "ENCOUNTER_ID" character varying,
    "CAREPLAN_CODE" bigint,
    "CAREPLAN_DESCRIPTION" character varying,
    "REASONCODE" bigint,
    "REASONDESCRIPTION" character varying
);


--
-- Name: conditions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conditions (
    "START" date,
    "STOP" date,
    "PATIENT_ID" character varying,
    "ENCOUNTER_ID" character varying,
    "CONDITION_CODE" bigint,
    "CONDITION_DESCRIPTION" character varying
);


--
-- Name: devices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.devices (
    "START" date,
    "STOP" date,
    "PATIENT_ID" character varying,
    "ENCOUNTER_ID" character varying,
    "DEVICE_CODE" bigint,
    "DEVICE_DESCRIPTION" character varying,
    "UDI" character varying
);


--
-- Name: encounters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.encounters (
    "ENCOUNTER_ID" character varying,
    "START" date,
    "STOP" date,
    "PATIENT_ID" character varying,
    "ORGANIZATION_ID" character varying,
    "PROVIDER_ID" character varying,
    "PAYER_ID" character varying,
    "ENCOUNTERCLASS" character varying,
    "ENCOUNTER_CODE" bigint,
    "ENCOUNTER_DESCRIPTION" character varying,
    "BASE_ENCOUNTER_COST" numeric,
    "TOTAL_CLAIM_COST" numeric,
    "PAYER_COVERAGE" numeric,
    "REASONCODE" bigint,
    "REASONDESCRIPTION" character varying
);


--
-- Name: imaging_studies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.imaging_studies (
    "IMAGING_STUDIES_ID" character varying,
    "DATE" date,
    "PATIENT_ID" character varying,
    "ENCOUNTER_ID" character varying,
    "BODYSITE_CODE" bigint,
    "BODYSITE_DESCRIPTION" character varying,
    "MODALITY_CODE" character varying,
    "MODALITY_DESCRIPTION" character varying,
    "SOP_CODE" character varying,
    "SOP_DESCRIPTION" character varying
);


--
-- Name: immunizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.immunizations (
    "DATE" date,
    "PATIENT_ID" character varying,
    "ENCOUNTER_ID" character varying,
    "IMMUNIZATION_CODE" bigint,
    "IMMUNIZATION_DESCRIPTION" character varying,
    "BASE_COST" numeric
);


--
-- Name: medications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.medications (
    "START" date,
    "STOP" date,
    "PATIENT_ID" character varying,
    "PAYER_ID" character varying,
    "ENCOUNTER_ID" character varying,
    "MEDICATION_CODE" bigint,
    "MEDICATION_DESCRIPTION" character varying,
    "BASE_COST" numeric,
    "PAYER_COVERAGE" numeric,
    "DISPENSES" integer,
    "TOTALCOST" numeric,
    "REASONCODE" bigint,
    "REASONDESCRIPTION" character varying
);


--
-- Name: observations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.observations (
    "DATE" date,
    "PATIENT_ID" character varying,
    "ENCOUNTER_ID" character varying,
    "OBSERVATION_CODE" character varying,
    "OBSERVATION_DESCRIPTION" character varying,
    "VALUE" character varying,
    "UNITS" character varying,
    "TYPE" text
);


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    "ORGANIZATION_ID" character varying,
    "NAME" text,
    "ADDRESS" text,
    "CITY" text,
    "STATE" text,
    "ZIP" character varying,
    "LAT" numeric,
    "LON" numeric,
    "PHONE" character varying,
    "REVENUE" numeric
);


--
-- Name: patients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.patients (
    "PATIENT_ID" character varying NOT NULL,
    "BIRTHDATE" date,
    "DEATHDATE" date,
    "SSN" character varying,
    "DRIVERS" character varying,
    "PASSPORT" character varying,
    "PREFIX" character varying,
    "FIRST" text,
    "LAST" text,
    "SUFFIX" character varying,
    "MAIDEN" character varying,
    "MARTIAL" character varying,
    "RACE" character varying,
    "ETHINICITY" character varying,
    "GENDER" character(1),
    "BIRTHPLACE" character varying,
    "ADDRESS" character varying,
    "CITY" character varying,
    "STATE" character varying,
    "COUNTY" character varying,
    "ZIP" character varying,
    "LAT" numeric,
    "LON" numeric,
    "HEALTHCARE_EXPENSES" numeric,
    "HEALTHCARE_COVERAGE" numeric
);


--
-- Name: payer_transitions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payer_transitions (
    "PATIENT_ID" character varying,
    "START_YEAR" integer,
    "END_YEAR" integer,
    "PAYER_ID" character varying,
    "OWNERSHIP" text
);


--
-- Name: payers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payers (
    "PAYER_ID" character varying,
    "NAME" text,
    "ADDRESS" character varying,
    "CITY" text,
    "STATE_HEADQUARTERED" text,
    "ZIP" character varying,
    "PHONE" character varying,
    "AMOUNT_COVERED" numeric,
    "AMOUNT_UNCOVERED" numeric,
    "REVENUE" numeric,
    "COVERED_ENCOUTERS" bigint,
    "UNCOVERED_ENCOUNTERS" bigint,
    "COVERED_MEDICATIONS" bigint,
    "UNCOVERED_MEDICATIONS" bigint,
    "COVERED_PROCEDURES" bigint,
    "UNCOVERED_PROCEDURES" bigint,
    "COVERED_IMMUNIZATIONS" bigint,
    "UNCOVERED_IMMUNIZATIONS" bigint,
    "UNIQUE_CUSTOMERS" bigint
);


--
-- Name: procedures; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.procedures (
    "DATE" date,
    "PATIENT_ID" character varying,
    "ENCOUNTER_ID" character varying,
    "PROCEDURE_CODE" bigint,
    "PROCEDURE_DESCRIPTION" character varying,
    "BASE_COST" numeric,
    "REASONCODE" bigint,
    "REASONDESCRIPTION" character varying
);


--
-- Name: providers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.providers (
    "PROVIDER_ID" character varying,
    "ORGANIZATION_ID" character varying,
    "NAME" text,
    "GENDER" "char",
    "SPECIALITY" text,
    "ADDRESS" character varying,
    "CITY" text,
    "STATE" text,
    "ZIP" character varying,
    "LAT" numeric,
    "LON" numeric
);


--
-- PostgreSQL database dump complete
--

