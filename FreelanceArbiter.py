# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

class FreelanceArbiter(gl.Contract):

    total_jobs: u256
    jobs: TreeMap[str, str]
    verdicts: TreeMap[str, str]

    def __init__(self) -> None:
        self.total_jobs = u256(0)
        self.jobs = TreeMap()
        self.verdicts = TreeMap()

    @gl.public.write
    def submit_job(
        self,
        job_id: str,
        title: str,
        requirements: str,
        deliverable_url: str,
        budget: str
    ) -> None:
        if not job_id or not title or not requirements:
            raise Exception("job_id, title and requirements are required")

        job = json.dumps({
            "job_id": job_id,
            "title": title,
            "requirements": requirements,
            "deliverable_url": deliverable_url,
            "budget": budget,
            "client": str(gl.message.sender_address),
            "status": "PENDING"
        })
        self.jobs[job_id] = job
        self.total_jobs = u256(int(self.total_jobs) + 1)

    @gl.public.write
    def judge_job(self, job_id: str) -> None:
        job_raw = self.jobs.get(job_id, "")
        if not job_raw:
            raise Exception("Job not found")

        job = json.loads(job_raw)

        def get_leader_result() -> str:
            deliverable_data = ""
            if job.get("deliverable_url"):
                try:
                    response = gl.nondet.web.get(job["deliverable_url"])
                    deliverable_data = response.body.decode("utf-8")[:1500]
                except:
                    deliverable_data = "Deliverable data unavailable"

            prompt = f"""You are an impartial freelance work arbitrator.

Job Title: {job['title']}
Client Requirements: {job['requirements']}
Budget: {job['budget']}
Deliverable URL: {job.get('deliverable_url', 'Not provided')}
Deliverable Content: {deliverable_data}

Review this freelance work submission and return ONLY valid JSON:
{{"verdict": "APPROVED", "score": 80, "quality": "HIGH", "reasons": ["reason1", "reason2"], "risk_flags": [], "confidence": "HIGH"}}

verdict must be one of: APPROVED, REJECTED, NEEDS_REVISION
score must be integer 0-100
quality must be: LOW, MEDIUM, or HIGH
confidence must be: LOW, MEDIUM, or HIGH"""

            return gl.nondet.exec_prompt(prompt)

        def validator_fn(leader_result: str) -> bool:
            prompt = f"""A freelance arbitrator evaluated this job:
Title: {job['title']}
Requirements: {job['requirements']}
Leader verdict: {leader_result}

Is this verdict reasonable? Reply with only: true or false"""
            output = gl.nondet.exec_prompt(prompt)
            return "true" in output.strip().lower()

        result = gl.eq_principle.nondet(get_leader_result, validator_fn)

        self.verdicts[job_id] = json.dumps({
            "job_id": job_id,
            "verdict_raw": result,
            "judged": True
        })

    @gl.public.view
    def get_job(self, job_id: str) -> str:
        return self.jobs.get(job_id, "")

    @gl.public.view
    def get_verdict(self, job_id: str) -> str:
        return self.verdicts.get(job_id, "")

    @gl.public.view
    def get_total(self) -> u256:
        return self.total_jobs
