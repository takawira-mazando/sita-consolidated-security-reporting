-- ============================================================================
-- seed-hr-system.sql - SIMULATED EXTERNAL HR SYSTEM employee master
-- ============================================================================
-- Idempotent seed for the hr.employees table that stands in for SITA's real
-- HR/PERSAL system. The platform pulls from this via POST /admin/hr/sim/sync
-- (admin-guarded) which runs the exact same pipeline as a real HR feed.
--
-- Contains:
--   * EMP-1xxx  - "legacy" staff already present in identity.persons
--                 (EMP-1001 Thabo Mokoena is the existing terminated row and
--                 is re-synced as active to prove reactivation works)
--   * EMP-200x  - one employee record PER demo persona, so each demo account
--                 has a matching HR record from which an account can be
--                 provisioned (HR-only user creation).
--   * EMP-300x  - provincial staff (gp-health, gp-education, wc-health).
--   * EMP-1008  - a terminated employee, proving linked accounts are
--                 soft-disabled by the sync.
--
-- Rerunnable: every employee upserts on employee_number (refreshable source).
-- ============================================================================

INSERT INTO hr.employees (
    employee_number, id_number, title, initials, first_name, surname,
    display_name, email, job_title, org_unit, department_code, branch_code,
    manager_employee_number, manager_name, work_phone, location,
    employment_status, clearance_level, hire_date, termination_date
) VALUES
-- --- "legacy" identity.persons owners --------------------------------------
('EMP-1001', '8001015800089', 'Mr', 'TM', 'Thabo', 'Mokoena',
 'Thabo Mokoena', 'thabo.mokoena@treasury.gov.za',
 'ICT Security Manager', 'Corporate Services & ICT', 'treasury', 'treasury-ict',
 'EMP-1002', 'Naledi Khumalo', '012 315 1001', '240 Vermeulen St, Pretoria',
 'active', 'confidential', '2019-03-01', NULL),
('EMP-1002', '7905150267084', 'Ms', 'NK', 'Naledi', 'Khumalo',
 'Naledi Khumalo', 'naledi.khumalo@treasury.gov.za',
 'Director General', 'Office of the Accountant-General', 'treasury', 'treasury-ag',
 NULL, NULL, '012 315 1002', '240 Vermeulen St, Pretoria',
 'active', 'top-secret', '2015-06-15', NULL),
('EMP-1003', '8109115432087', 'Mr', 'SD', 'Sipho', 'Dlamini',
 'Sipho Dlamini', 'sipho.dlamini@dha.gov.za',
 'Director: Information Services', 'Information Services (CIO)', 'home-affairs-digital', 'dha-digital',
 'EMP-1001', 'Thabo Mokoena', '012 406 1003', '230 Johannes Ramokhoase St, Pretoria',
 'active', 'secret', '2017-02-20', NULL),
('EMP-1004', '8807230812045', 'Ms', 'AP', 'Aisha', 'Patel',
 'Aisha Patel', 'aisha.patel@dha.gov.za',
 'Head: Civic Services', 'Civic Services', 'home-affairs-digital', 'dha-civic',
 'EMP-1003', 'Sipho Dlamini', '012 406 1004', '230 Johannes Ramokhoase St, Pretoria',
 'active', 'confidential', '2018-08-06', NULL),
('EMP-1005', '7601126045083', 'Mr', 'JvdM', 'Johan', 'van der Merwe',
 'Johan van der Merwe', 'johan.vdm@dpsa.gov.za',
 'e-Government Services Manager', 'e-Government Services and Information Management', 'dpsa-hr', 'dpsa-ict',
 'EMP-1001', 'Thabo Mokoena', '012 314 1005', '546 Edmond St, Arcadia, Pretoria',
 'active', 'secret', '2014-11-03', NULL),
('EMP-1006', '9204051776032', 'Ms', 'LN', 'Lerato', 'Nkosi',
 'Lerato Nkosi', 'lerato.nkosi@justice.gov.za',
 'ICT Manager', 'Information and Communication Technology', 'justice-document', 'doj-ict',
 'EMP-1001', 'Thabo Mokoena', '012 315 1006', 'Momentum Centre, Pretoria',
 'active', 'confidential', '2020-04-13', NULL),
('EMP-1007', '8501284228071', 'Ms', 'ZM', 'Zanele', 'Mthembu',
 'Zanele Mthembu', 'zanele.mthembu@health.gov.za',
 'NHI Programme Manager', 'National Health Insurance', 'health-legacy', 'doh-nhi',
 'EMP-1001', 'Thabo Mokoena', '012 395 1007', 'Civitas Building, Pretoria',
 'active', 'confidential', '2016-09-19', NULL),
('EMP-1008', '8309053309046', 'Mr', 'PB', 'Pieter', 'Botha',
 'Pieter Botha', 'pieter.botha@treasury.gov.za',
 'Network Specialist', 'Corporate Services & ICT', 'treasury', 'treasury-ict',
 'EMP-1001', 'Thabo Mokoena', '012 315 1008', '240 Vermeulen St, Pretoria',
 'terminated', 'confidential', '2016-01-11', '2026-05-30'),

-- --- demo persona employee records (account provisioning source) ------------
('EMP-2001', '7802210812046', 'Dr', 'EN', 'Emma', 'Ncube',
 'Emma Ncube', 'exec@example.com',
 'Executive Director', 'Cabinet Services', 'presidency', 'presidency-cabinet',
 'EMP-1002', 'Naledi Khumalo', '012 300 2001', 'Union Buildings, Pretoria',
 'active', 'top-secret', '2013-05-01', NULL),
('EMP-2002', '9101125836029', 'Mr', 'KC', 'Kabelo', 'Chauke',
 'Kabelo Chauke', 'soc@example.com',
 'SOC Analyst', 'Information Services (CIO)', 'home-affairs-digital', 'dha-digital',
 'EMP-1003', 'Sipho Dlamini', '012 406 2002', '230 Johannes Ramokhoase St, Pretoria',
 'active', 'secret', '2021-07-05', NULL),
('EMP-2003', '9409180732041', 'Ms', 'TS', 'Thandi', 'Sithole',
 'Thandi Sithole', 'appsec@example.com',
 'Application Security Engineer', 'Corporate Services & ICT', 'treasury', 'treasury-ict',
 'EMP-1001', 'Thabo Mokoena', '012 315 2003', '240 Vermeulen St, Pretoria',
 'active', 'confidential', '2022-01-17', NULL),
('EMP-2004', '9003065109087', 'Mr', 'RM', 'Riaan', 'Marais',
 'Riaan Marais', 'dbsec@example.com',
 'Database Security Engineer', 'e-Government Services and Information Management', 'dpsa-hr', 'dpsa-ict',
 'EMP-1005', 'Johan van der Merwe', '012 314 2004', '546 Edmond St, Arcadia, Pretoria',
 'active', 'secret', '2019-10-28', NULL),
('EMP-2005', '8704190864022', 'Ms', 'AM', 'Anele', 'Mbatha',
 'Anele Mbatha', 'compliance@example.com',
 'Compliance Officer', 'Corporate Services', 'justice-document', 'doj-corporate',
 'EMP-1006', 'Lerato Nkosi', '012 315 2005', 'Momentum Centre, Pretoria',
 'active', 'confidential', '2018-03-12', NULL),
('EMP-2006', '9307291153048', 'Mr', 'DP', 'Devon', 'Pillay',
 'Devon Pillay', 'sre@example.com',
 'Site Reliability Engineer', 'Corporate Services & ICT', 'treasury', 'treasury-ict',
 'EMP-1001', 'Thabo Mokoena', '012 315 2006', '240 Vermeulen St, Pretoria',
 'active', 'confidential', '2020-06-01', NULL),
('EMP-2007', '9605124308075', 'Ms', 'MN', 'Mpho', 'Ndlovu',
 'Mpho Ndlovu', 'deptadmin@example.com',
 'Department Administrator', 'Corporate Services & ICT', 'treasury', 'treasury-ict',
 'EMP-1001', 'Thabo Mokoena', '012 315 2007', '240 Vermeulen St, Pretoria',
 'active', 'confidential', '2022-09-05', NULL),
('EMP-2008', '8806107729041', 'Mr', 'BS', 'Bradley', 'Swart',
 'Bradley Swart', 'branchadmin@example.com',
 'Branch Administrator', 'Budget Office', 'treasury', 'treasury-budget',
 'EMP-1002', 'Naledi Khumalo', '012 315 2008', '240 Vermeulen St, Pretoria',
 'active', 'confidential', '2017-04-24', NULL),
('EMP-2009', '8301275448036', 'Ms', 'NK', 'Nomsa', 'Kekana',
 'Nomsa Kekana', 'transversal@example.com',
 'Transversal Administrator', 'Corporate Management', 'presidency', 'presidency-corporate',
 'EMP-1002', 'Naledi Khumalo', '012 300 2009', 'Union Buildings, Pretoria',
 'active', 'top-secret', '2015-08-03', NULL),
('EMP-2010', '9008236612079', 'Mr', 'SM', 'Sibusiso', 'Mahlangu',
 'Sibusiso Mahlangu', 'provincesoc@example.com',
 'Provincial SOC Lead', 'Provincial Health Operations', 'gp-health', NULL,
 'EMP-1001', 'Thabo Mokoena', '011 355 2010', 'Joubert St, Johannesburg',
 'active', 'secret', '2019-02-11', NULL),
('EMP-2011', '8507150924063', 'Mr', 'GM', 'Gift', 'Molefe',
 'Gift Molefe', 'admin@example.com',
 'System Administrator', 'Policy and Research Services', 'presidency', 'presidency-policy',
 'EMP-1002', 'Naledi Khumalo', '012 300 2011', 'Union Buildings, Pretoria',
 'active', 'top-secret', '2014-10-06', NULL),

-- --- provincial staff -------------------------------------------------------
('EMP-3001', '7703243127085', 'Ms', 'NZ', 'Nonhlanhla', 'Zulu',
 'Nonhlanhla Zulu', 'nonhlanhla.zulu@gauteng.gov.za',
 'Provincial Health ICT Manager', 'Provincial Health Operations', 'gp-health', NULL,
 'EMP-1001', 'Thabo Mokoena', '011 355 3001', 'Joubert St, Johannesburg',
 'active', 'confidential', '2016-07-18', NULL),
('EMP-3002', '9501162588044', 'Mr', 'TM', 'Tshepo', 'Molefe',
 'Tshepo Molefe', 'tshepo.molefe@gauteng.gov.za',
 'Provincial Education ICT Officer', 'Provincial Education Operations', 'gp-education', NULL,
 'EMP-1001', 'Thabo Mokoena', '011 355 3002', 'Joubert St, Johannesburg',
 'active', 'confidential', '2021-11-22', NULL),
('EMP-3003', '8902084196072', 'Ms', 'FA', 'Fatima', 'Abrahams',
 'Fatima Abrahams', 'fatima.abrahams@westerncape.gov.za',
 'Provincial Health Security Officer', 'Provincial Health Operations', 'wc-health', NULL,
 'EMP-1001', 'Thabo Mokoena', '021 483 3003', 'Dorp St, Cape Town',
 'active', 'secret', '2018-05-14', NULL)

ON CONFLICT (employee_number) DO UPDATE SET
    id_number               = EXCLUDED.id_number,
    title                   = EXCLUDED.title,
    initials                = EXCLUDED.initials,
    first_name              = EXCLUDED.first_name,
    surname                 = EXCLUDED.surname,
    display_name            = EXCLUDED.display_name,
    email                   = EXCLUDED.email,
    job_title               = EXCLUDED.job_title,
    org_unit                = EXCLUDED.org_unit,
    department_code         = EXCLUDED.department_code,
    branch_code             = EXCLUDED.branch_code,
    manager_employee_number = EXCLUDED.manager_employee_number,
    manager_name            = EXCLUDED.manager_name,
    work_phone              = EXCLUDED.work_phone,
    location                = EXCLUDED.location,
    employment_status       = EXCLUDED.employment_status,
    clearance_level         = EXCLUDED.clearance_level,
    hire_date               = EXCLUDED.hire_date,
    termination_date        = EXCLUDED.termination_date,
    updated_at              = now();
