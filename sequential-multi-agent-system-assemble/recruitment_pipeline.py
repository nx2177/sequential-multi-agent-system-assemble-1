import os
import json
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import itertools
from langchain_anthropic import ChatAnthropic  # Updated import
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage

@dataclass
class AgentPrompt:
    """Represents a prompt configuration for an agent"""
    name: str
    style: str
    template: str

@dataclass
class AgentResult:
    """Stores the result from an agent"""
    agent_name: str
    output: Any

@dataclass
class CandidateResult:
    """Stores the results for a single candidate"""
    resume_id: str
    a_result: AgentResult
    b_result: AgentResult
    c_result: Optional[AgentResult] = None
    final_rank: Optional[Any] = None
    filtered_out: bool = False
    filter_reason: Optional[str] = None

@dataclass
class PipelineResult:
    """Stores the results from a full pipeline run with multiple candidates"""
    sequence: str
    candidate_results: List[CandidateResult]
    filtered_out: List[str]
    ranked_candidates: List[Tuple[str, Any]]

class RecruitmentAgent:
    """Base class for all recruitment agents"""
    
    def __init__(self, prompt: AgentPrompt, model_name: str = "claude-3-opus-20240229"):
        self.prompt = prompt
        if "claude" in model_name.lower():
            self.llm = ChatAnthropic(model=model_name)

    def run(self, inputs: Dict[str, Any]) -> Any:
        """Run the agent with the given inputs"""
        prompt_template = PromptTemplate.from_template(self.prompt.template)
        formatted_prompt = prompt_template.format(**inputs)
        
        # Using invoke instead of the deprecated __call__ method
        result = self.llm.invoke([HumanMessage(content=formatted_prompt)])
        
        return result.content

    def extract_json_from_text(self, text: str) -> Dict:
        """Extract JSON from text, handling potential text wrappers"""
        # Try to find JSON-like content in the response
        import re
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
        match = re.search(json_pattern, text)
        
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        # If no valid JSON found, return a simple dict with the text
        return {"extracted_text": text}

class KeywordExtractionAgent(RecruitmentAgent):
    """Agent for extracting keywords from resume (Category A)"""
    
    def run(self, resume: str, resume_id: str) -> Dict[str, List[str]]:
        """Extract keywords from resume"""
        result = super().run({"resume": resume})
        try:
            return json.loads(result)
        except:
            # Try to extract JSON from the response
            try:
                return self.extract_json_from_text(result)
            except:
                # If all else fails, create a structured response
                return {
                    "technical_skills": ["unknown"],
                    "soft_skills": ["unknown"],
                    "education": ["unknown"],
                    "experience": ["unknown"],
                    "extracted_text": result
                }

class CandidateFilteringAgent(RecruitmentAgent):
    """Agent for filtering candidates (Category B)"""
    
    def run(self, keywords: Dict[str, List[str]], job_description: str, resume_id: str) -> Dict[str, Any]:
        """Filter candidate based on keywords and job description"""
        # Ensure keywords is properly serialized
        keywords_str = json.dumps(keywords)
        
        result = super().run({
            "keywords": keywords_str,
            "job_description": job_description
        })
        
        try:
            parsed_result = json.loads(result)
            # Check if the candidate meets requirements
            meets_requirements = parsed_result.get("meets_requirements", True)  # Default to True if not specified
            parsed_result["filtered_out"] = not meets_requirements
            if not meets_requirements:
                parsed_result["filter_reason"] = parsed_result.get("filter_reason", "Does not meet minimum requirements")
            return parsed_result
        except:
            # Try to extract JSON from the response
            try:
                parsed_result = self.extract_json_from_text(result)
                meets_requirements = parsed_result.get("meets_requirements", True)
                parsed_result["filtered_out"] = not meets_requirements
                if not meets_requirements:
                    parsed_result["filter_reason"] = parsed_result.get("filter_reason", "Does not meet minimum requirements")
                return parsed_result
            except:
                # If we can't parse JSON, assume the candidate passes by default
                # We'll include the raw result for debugging
                return {
                    "meets_requirements": True,
                    "match_score": 50,  # Default middle score
                    "strengths": ["Unable to parse response"],
                    "gaps": ["Unable to parse response"],
                    "overall_assessment": result[:100] + "...",  # First 100 chars of response
                    "filtered_out": False,
                    "raw_response": result
                }

class CandidateRankingAgent(RecruitmentAgent):
    """Agent for ranking candidates (Category C)"""
    
    def run(self, filtered_profile: Dict[str, Any], job_description: str, resume_id: str) -> Dict[str, Any]:
        """Rank candidate based on filtered profile and job description"""
        # Skip if the candidate was filtered out explicitly
        if filtered_profile.get("filtered_out", False):
            return {
                "ranking_score": 0,
                "justification": "Candidate filtered out",
                "filtered_out": True,
                "filter_reason": filtered_profile.get("filter_reason", "Failed requirements")
            }
        
        # Ensure filtered_profile is properly serialized
        filtered_profile_str = json.dumps(filtered_profile)
        
        result = super().run({
            "filtered_profile": filtered_profile_str,
            "job_description": job_description
        })
        
        try:
            return json.loads(result)
        except:
            # Try to extract JSON from the response
            try:
                return self.extract_json_from_text(result)
            except:
                # If we still can't parse, return a default ranking
                return {
                    "ranking_score": 5,  # Default middle score
                    "justification": "Score based on default ranking (parsing error)",
                    "raw_response": result
                }
    
    def rank_candidates(self, filtered_profiles: List[Dict[str, Any]], job_description: str) -> Tuple[List[str], List[Tuple[str, Dict[str, Any]]]]:
        """Rank multiple candidates based on their filtered profiles"""
        # First, separate filtered out candidates
        filtered_out = []
        valid_candidates = []
        
        for profile in filtered_profiles:
            resume_id = profile.get("resume_id", "unknown")
            
            # Check if candidate was filtered out
            if profile.get("filtered_out", False) or profile.get("filtered_data", {}).get("filtered_out", False):
                filtered_out.append(resume_id)
            else:
                valid_candidates.append(profile)
        
        # If all candidates were filtered out, return early
        if not valid_candidates:
            return filtered_out, []
        
        # Rank valid candidates
        ranked_results = []
        
        for profile in valid_candidates:
            resume_id = profile.get("resume_id", "unknown")
            result = self.run(profile.get("filtered_data", {}), job_description, resume_id)
            
            # Extract ranking score (with fallbacks)
            rank_score = 0
            if isinstance(result, dict):
                rank_score = result.get("ranking_score", result.get("overall_ranking", 5))
            
            ranked_results.append((resume_id, rank_score, result))
            
        # Sort by rank score (higher is better)
        sorted_results = sorted(ranked_results, key=lambda x: x[1], reverse=True)
        
        # Return as (filtered_out_list, [(candidate_id, full_ranking_result)])
        return filtered_out, [(cand_id, result) for cand_id, _, result in sorted_results]

class AgentFactory:
    """Factory for creating agents with different prompting styles"""
    
    @staticmethod
    def create_keyword_extraction_agents() -> List[KeywordExtractionAgent]:
        """Create two different keyword extraction agents"""
        prompts = [
            AgentPrompt(
                name="A1",
                style="Concise and direct",
                template="""
                Extract the most important skills, qualifications, and experience from the following resume.
                Be concise and list only the key information.
                
                You MUST format your response as a valid JSON object with the following structure:
                {{"technical_skills": ["skill1", "skill2", ...],
                "soft_skills": ["skill1", "skill2", ...],
                "education": ["degree1", "degree2", ...],
                "experience": ["exp1", "exp2", ...]}}
                
                Resume:
                {resume}
                
                Return ONLY the JSON object without any additional text.
                """
            ),
            AgentPrompt(
                name="A2",
                style="Detailed and conversational",
                template="""
                I'd like you to carefully analyze this resume and extract comprehensive information about the candidate.
                Please take your time to thoroughly identify all skills, experiences, qualifications, and other relevant information.
                Consider both explicit mentions and implied skills based on their work history.
                
                For technical skills, look for programming languages, tools, platforms, methodologies, etc.
                For soft skills, identify traits like leadership, communication, project management, etc.
                For education, capture degrees, institutions, relevant coursework, certifications, etc.
                For experience, summarize roles, responsibilities, achievements, and duration.
                
                You MUST structure your output as a valid JSON object with these categories:
                {{"technical_skills": ["skill1", "skill2", ...],
                "soft_skills": ["skill1", "skill2", ...],
                "education": ["degree1", "degree2", ...],
                "experience": ["exp1", "exp2", ...],
                "additional_keywords": ["keyword1", "keyword2", ...]}}
                
                Resume to analyze:
                {resume}
                
                Return ONLY the JSON object without any additional text.
                """
            )
        ]
        
        return [KeywordExtractionAgent(prompt) for prompt in prompts]
    
    @staticmethod
    def create_candidate_filtering_agents() -> List[CandidateFilteringAgent]:
        """Create two different candidate filtering agents"""
        prompts = [
            AgentPrompt(
                name="B1",
                style="Analytical and structured",
                template="""
                Analyze the candidate's keywords against the job description.
                First, check if the candidate meets all HARD REQUIREMENTS for the job:
                1. Required technical skills (e.g., Python, Machine Learning)
                2. Minimum education (e.g., Bachelor's degree)
                3. Minimum years of experience (e.g., 5+ years)
                
                If the candidate fails ANY hard requirement, they should be FILTERED OUT.
                
                Keywords from resume:
                {keywords}
                
                Job Description:
                {job_description}
                
                You MUST provide your assessment as a valid JSON with the following structure:
                {{"meets_requirements": true/false,
                "match_score": 0-100,
                "strengths": ["strength1", "strength2", ...],
                "gaps": ["gap1", "gap2", ...],
                "overall_assessment": "brief statement",
                "filtered_out": false,
                "filter_reason": "Only include if filtered_out is true"}}
                
                Return ONLY the JSON object without any additional text.
                """
            ),
            AgentPrompt(
                name="B2",
                style="Evaluative and detailed",
                template="""
                You are an experienced technical recruiter evaluating a candidate for a position.
                Your first task is to determine if the candidate meets all HARD REQUIREMENTS:
                
                1. Check for MUST-HAVE skills and qualifications in the job description
                2. Check for required education level
                3. Check for minimum experience requirements
                
                If the candidate fails ANY hard requirement, they must be FILTERED OUT immediately.
                
                Job Description:
                {job_description}
                
                Candidate's Keywords:
                {keywords}
                
                Your evaluation tasks:
                1. Identify any hard requirements the candidate fails
                2. If they pass hard requirements, compare their profile against the job description
                3. Identify specific matches between requirements and qualifications
                4. Note any missing skills or qualifications
                5. Evaluate how well their experience aligns with the role's responsibilities
                
                You MUST provide a comprehensive evaluation in valid JSON format:
                {{"meets_requirements": true/false,
                "match_score": 0-100,
                "requirement_analysis": [
                    {{"requirement": "req1", "met": true/false, "evidence": "..."}}
                ],
                "key_strengths": ["strength1", "strength2", ...],
                "key_gaps": ["gap1", "gap2", ...],
                "suitability_assessment": "detailed paragraph",
                "filtered_out": false/true,
                "filter_reason": "Only include if filtered_out is true"}}
                
                Return ONLY the JSON object without any additional text.
                """
            )
        ]
        
        return [CandidateFilteringAgent(prompt) for prompt in prompts]
    
    @staticmethod
    def create_candidate_ranking_agents() -> List[CandidateRankingAgent]:
        """Create two different candidate ranking agents"""
        prompts = [
            AgentPrompt(
                name="C1",
                style="Numerical and objective",
                template="""
                Based on the filtered candidate profile and job description, assign a numerical ranking to the candidate.
                Only evaluate candidates who have passed the filtering stage.
                
                Filtered Candidate Profile:
                {filtered_profile}
                
                Job Description:
                {job_description}
                
                Provide a ranking score from 1-10 (10 being the highest) and justify your score.
                
                You MUST format your response as a valid JSON:
                {{"ranking_score": 7,
                "justification": "brief explanation"}}
                
                Return ONLY the JSON object without any additional text.
                """
            ),
            AgentPrompt(
                name="C2",
                style="Comprehensive and contextual",
                template="""
                As a senior hiring manager, evaluate this candidate's suitability for the role based on their filtered profile.
                Only evaluate candidates who have passed the filtering stage.
                Consider not just technical fit, but also potential culture fit, growth potential, and long-term value.
                
                Filtered Candidate Profile:
                {filtered_profile}
                
                Job Description:
                {job_description}
                
                Provide a detailed multi-dimensional assessment with these components:
                
                1. Overall fit score (1-10 scale, 10 being perfect)
                2. Technical capability score (1-10)
                3. Experience relevance score (1-10)
                4. Potential growth/learning curve score (1-10)
                5. Detailed justification for each score
                6. Final recommendation (Reject, Consider, Interview, Strong Recommend)
                
                You MUST return your evaluation as a valid JSON object:
                {{"overall_ranking": 7,
                "technical_score": 8,
                "experience_score": 7,
                "potential_score": 6,
                "justification": {{
                    "technical": "explanation",
                    "experience": "explanation",
                    "potential": "explanation"
                }},
                "recommendation": "Interview",
                "additional_notes": "any other observations"}}
                
                Return ONLY the JSON object without any additional text.
                """
            )
        ]
        
        return [CandidateRankingAgent(prompt) for prompt in prompts]

class RecruitmentPipeline:
    """Main pipeline for running the recruitment process"""
    
    def __init__(self, model_name: str = "claude-3-opus-20240229"):
        self.model_name = model_name
        # Create all agents
        self.a_agents = AgentFactory.create_keyword_extraction_agents()
        self.b_agents = AgentFactory.create_candidate_filtering_agents()
        self.c_agents = AgentFactory.create_candidate_ranking_agents()
        
    def run_all_pipelines(self, resumes: Dict[str, str], job_description: str) -> List[PipelineResult]:
        """Run all possible combinations of agents on multiple resumes"""
        results = []
        
        # Generate all possible combinations (2x2x2=8)
        for a_agent, b_agent, c_agent in itertools.product(self.a_agents, self.b_agents, self.c_agents):
            sequence = f"{a_agent.prompt.name}->{b_agent.prompt.name}->{c_agent.prompt.name}"
            print(f"Running sequence: {sequence}")
            
            # Process each resume through the pipeline
            candidate_results = []
            all_filtered_profiles = []
            
            for resume_id, resume_text in resumes.items():
                print(f"  Processing resume: {resume_id}")
                
                # Stage A: Extract keywords
                a_output = a_agent.run(resume_text, resume_id)
                a_result = AgentResult(a_agent.prompt.name, a_output)
                
                # Stage B: Filter candidate
                b_output = b_agent.run(a_output, job_description, resume_id)
                b_result = AgentResult(b_agent.prompt.name, b_output)
                
                # Check if candidate is filtered out
                filtered_out = b_output.get("filtered_out", False)
                filter_reason = b_output.get("filter_reason", None) if filtered_out else None
                
                if filtered_out:
                    print(f"    Candidate filtered out: {filter_reason}")
                    # Create a candidate result without C stage
                    candidate_result = CandidateResult(
                        resume_id=resume_id,
                        a_result=a_result,
                        b_result=b_result,
                        filtered_out=True,
                        filter_reason=filter_reason
                    )
                else:
                    # Stage C: Rank individual candidate
                    c_output = c_agent.run(b_output, job_description, resume_id)
                    c_result = AgentResult(c_agent.prompt.name, c_output)
                    
                    # Extract the final rank for this candidate
                    if isinstance(c_output, dict):
                        final_rank = c_output.get("ranking_score") or c_output.get("overall_ranking")
                    else:
                        final_rank = None
                    
                    # Store the candidate result
                    candidate_result = CandidateResult(
                        resume_id=resume_id,
                        a_result=a_result,
                        b_result=b_result,
                        c_result=c_result,
                        final_rank=final_rank,
                        filtered_out=False
                    )
                
                candidate_results.append(candidate_result)
                
                # Store the filtered profile for final ranking
                enhanced_profile = {
                    "resume_id": resume_id,
                    "keywords": a_output,
                    "filtered_data": b_output,
                    "filtered_out": filtered_out
                }
                all_filtered_profiles.append(enhanced_profile)
                
            # Rank all non-filtered candidates against each other
            filtered_out_ids, ranked_candidates = c_agent.rank_candidates(all_filtered_profiles, job_description)
            
            # Create the pipeline result
            pipeline_result = PipelineResult(
                sequence=sequence,
                candidate_results=candidate_results,
                filtered_out=filtered_out_ids,
                ranked_candidates=ranked_candidates
            )
            
            results.append(pipeline_result)
            
        return results
    
    def evaluate_results(self, results: List[PipelineResult]) -> Dict[str, Dict]:
        """Evaluate results across all pipelines"""
        # For each pipeline, get the filtered out candidates and ranked list
        pipeline_results = {}
        
        for r in results:
            pipeline_results[r.sequence] = {
                "filtered_out": r.filtered_out,
                "final_ranking": [
                    {"id": cand_id, "score": rank.get("ranking_score", rank.get("overall_ranking", 0)) if isinstance(rank, dict) else 0}
                    for cand_id, rank in r.ranked_candidates
                ]
            }
            
        return pipeline_results

def load_resumes(resume_paths: List[str]) -> Dict[str, str]:
    """Load multiple resumes from files"""
    resumes = {}
    
    for path in resume_paths:
        with open(path, 'r', encoding='utf-8') as f:
            # Use filename without extension as resume_id
            resume_id = os.path.basename(path).split('.')[0]
            resumes[resume_id] = f.read()
    
    return resumes

def main(resume_paths: List[str], job_description_path: str):
    """Main function to run the recruitment pipeline"""
    # Load resumes and job description
    if not resume_paths or not job_description_path:
        raise ValueError("Resume paths and job description path must be provided")
    
    resumes = load_resumes(resume_paths)
    with open(job_description_path, 'r', encoding='utf-8') as f:
        job_description = f.read()
    
    # Initialize pipeline
    pipeline = RecruitmentPipeline(model_name="claude-3-opus-20240229")
    
    # Run all pipelines
    results = pipeline.run_all_pipelines(resumes, job_description)
    
    # Evaluate results
    pipeline_results = pipeline.evaluate_results(results)
    
    # Print results for each pipeline
    print("\nRecruitment Pipeline Results:")
    print("=" * 50)
    
    for sequence, result in pipeline_results.items():
        print(f"\n{sequence}:")
        
        if result["filtered_out"]:
            print(f"  Filtered out: {', '.join(result['filtered_out'])}")
        else:
            print("  No candidates filtered out")
        
        print("  Final Ranking:")
        for i, candidate in enumerate(result["final_ranking"], 1):
            print(f"    {i}. {candidate['id']} (Score: {candidate['score']})")
    
    # Save detailed results to file
    with open('pipeline_results.json', 'w') as f:
        json.dump(
            [{
                "sequence": r.sequence,
                "filtered_out": r.filtered_out,
                "candidates": [{
                    "resume_id": cr.resume_id,
                    "a_output": cr.a_result.output,
                    "b_output": cr.b_result.output,
                    "c_output": cr.c_result.output if not cr.filtered_out else None,
                    "individual_rank": cr.final_rank if not cr.filtered_out else None,
                    "filtered_out": cr.filtered_out,
                    "filter_reason": cr.filter_reason
                } for cr in r.candidate_results],
                "final_ranking": [
                    {"id": cand_id, "score": rank.get("ranking_score", rank.get("overall_ranking", 0)) if isinstance(rank, dict) else 0}
                    for cand_id, rank in r.ranked_candidates
                ]
            } for r in results],
            f,
            indent=2,
            default=lambda o: repr(o) if not isinstance(o, (dict, list, str, int, float, bool, type(None))) else o
        )
    
    print(f"\nDetailed results saved to pipeline_results.json")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the recruitment pipeline")
    parser.add_argument("--resumes", nargs='+', required=True, help="Paths to resume files")
    parser.add_argument("--job", "-j", dest="job_description", required=True, help="Path to the job description file")
    
    args = parser.parse_args()
    
    main(args.resumes, args.job_description)
