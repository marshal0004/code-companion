"""Advanced Accuracy Systems for CodeCompanion

Additional systems to achieve 95%+ accuracy:
1. Pre-Execution Validator
2. Confidence Calibrator
3. Error Pattern Recognizer
4. Code Quality Scorer
5. Iterative Refinement Engine
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib


# ============================================
# 1. PRE-EXECUTION VALIDATOR
# ============================================

@dataclass
class ValidationResult:
    """Result of pre-execution validation"""
    valid: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    blocking_issues: List[str]


class PreExecutionValidator:
    """
    Validates actions BEFORE execution to catch errors early.
    
    Checks:
    - File path validity
    - Code syntax (before write)
    - Import availability
    - Dependency satisfaction
    - Potential conflicts
    """
    
    def __init__(self, workspace_root: str):
        self.workspace = Path(workspace_root)
    
    def validate_action(self, action: Dict) -> ValidationResult:
        """Validate an action before execution"""
        issues = []
        suggestions = []
        blocking = []
        confidence = 1.0
        
        tool = action.get('tool', action.get('action', ''))
        args = action.get('args', {})
        
        # Validate based on tool type
        if tool == 'write_file':
            result = self._validate_write_file(args)
        elif tool == 'edit_file':
            result = self._validate_edit_file(args)
        elif tool == 'run_command':
            result = self._validate_command(args)
        else:
            return ValidationResult(
                valid=True,
                confidence=0.9,
                issues=[],
                suggestions=[],
                blocking_issues=[]
            )
        
        return result
    
    def _validate_write_file(self, args: Dict) -> ValidationResult:
        """Validate file write operation"""
        issues = []
        suggestions = []
        blocking = []
        confidence = 1.0
        
        path = args.get('path', '')
        content = args.get('content', '')
        
        # Check 1: Path validity
        if not path:
            blocking.append("No file path specified")
            confidence = 0.0
        elif '..' in path:
            blocking.append("Path traversal detected")
            confidence = 0.0
        
        # Check 2: Content not empty
        if not content or not content.strip():
            issues.append("Content is empty")
            confidence -= 0.2
        
        # Check 3: Python syntax (for .py files)
        if path.endswith('.py') and content:
            try:
                import ast
                ast.parse(content)
            except SyntaxError as e:
                blocking.append(f"Python syntax error at line {e.lineno}: {e.msg}")
                confidence = 0.0
        
        # Check 4: JSON syntax (for .json files)
        if path.endswith('.json') and content:
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                blocking.append(f"JSON syntax error: {e}")
                confidence = 0.0
        
        # Check 5: File overwrite warning
        full_path = self.workspace / path
        if full_path.exists():
            issues.append(f"File exists and will be overwritten: {path}")
            suggestions.append("Consider using edit_file for modifications")
            confidence -= 0.1
        
        # Check 6: Directory exists
        parent_dir = full_path.parent
        if not parent_dir.exists():
            issues.append(f"Parent directory doesn't exist: {parent_dir}")
            suggestions.append("Directory will be created")
        
        return ValidationResult(
            valid=len(blocking) == 0,
            confidence=max(confidence, 0.0),
            issues=issues,
            suggestions=suggestions,
            blocking_issues=blocking
        )
    
    def _validate_edit_file(self, args: Dict) -> ValidationResult:
        """Validate file edit operation"""
        issues = []
        suggestions = []
        blocking = []
        confidence = 1.0
        
        path = args.get('path', '')
        old_text = args.get('old_text', '')
        new_text = args.get('new_text', '')
        
        # Check 1: Path and text provided
        if not path:
            blocking.append("No file path specified")
            confidence = 0.0
        
        if not old_text:
            blocking.append("No old_text specified for edit")
            confidence = 0.0
        
        # Check 2: File exists
        full_path = self.workspace / path
        if not full_path.exists():
            blocking.append(f"File not found: {path}")
            confidence = 0.0
        else:
            # Check 3: old_text exists in file
            try:
                content = full_path.read_text()
                if old_text not in content:
                    blocking.append(f"old_text not found in file")
                    confidence = 0.0
                    suggestions.append("Read the file first to get exact text to replace")
            except Exception as e:
                issues.append(f"Could not read file: {e}")
                confidence -= 0.2
        
        # Check 4: Validate resulting code (for .py)
        if path.endswith('.py') and old_text and new_text and full_path.exists():
            try:
                content = full_path.read_text()
                new_content = content.replace(old_text, new_text, 1)
                import ast
                ast.parse(new_content)
            except SyntaxError as e:
                blocking.append(f"Edit would create syntax error at line {e.lineno}")
                confidence = 0.0
            except:
                pass
        
        return ValidationResult(
            valid=len(blocking) == 0,
            confidence=max(confidence, 0.0),
            issues=issues,
            suggestions=suggestions,
            blocking_issues=blocking
        )
    
    def _validate_command(self, args: Dict) -> ValidationResult:
        """Validate shell command"""
        issues = []
        suggestions = []
        blocking = []
        confidence = 1.0
        
        command = args.get('command', '')
        
        if not command:
            blocking.append("No command specified")
            return ValidationResult(False, 0.0, issues, suggestions, blocking)
        
        # Dangerous patterns
        dangerous = [
            (r'rm\s+-rf\s+/', "Dangerous recursive delete on root"),
            (r'rm\s+-rf\s+~', "Dangerous recursive delete on home"),
            (r'sudo', "Sudo commands not allowed"),
            (r'dd\s+if=', "dd command is dangerous"),
            (r'>\s*/dev/', "Writing to devices not allowed"),
            (r'mkfs', "Filesystem creation not allowed"),
            (r':\(\)\{', "Fork bomb detected"),
        ]
        
        for pattern, message in dangerous:
            if re.search(pattern, command, re.IGNORECASE):
                blocking.append(message)
                confidence = 0.0
        
        # Warning patterns
        warnings = [
            (r'rm\s', "Delete operation - ensure path is correct"),
            (r'mv\s', "Move operation - verify source and destination"),
            (r'pip install', "Consider adding to requirements.txt"),
            (r'npm install', "Consider adding to package.json"),
        ]
        
        for pattern, message in warnings:
            if re.search(pattern, command, re.IGNORECASE):
                issues.append(message)
                confidence -= 0.05
        
        return ValidationResult(
            valid=len(blocking) == 0,
            confidence=max(confidence, 0.0),
            issues=issues,
            suggestions=suggestions,
            blocking_issues=blocking
        )


# ============================================
# 2. CONFIDENCE CALIBRATOR
# ============================================

@dataclass
class ConfidenceFactors:
    """Factors that affect confidence"""
    understanding: float = 0.5
    plan_quality: float = 0.5
    file_familiarity: float = 0.5
    error_history: float = 1.0  # Reduced if errors occurred
    complexity_match: float = 0.5  # How well approach matches complexity
    verification_level: float = 0.5


class ConfidenceCalibrator:
    """
    Calibrates confidence scores based on multiple factors.
    Ensures we don't proceed with false confidence.
    """
    
    WEIGHTS = {
        'understanding': 0.20,
        'plan_quality': 0.20,
        'file_familiarity': 0.15,
        'error_history': 0.15,
        'complexity_match': 0.15,
        'verification_level': 0.15
    }
    
    def __init__(self):
        self.history: List[Dict] = []
        self.session_errors: int = 0
        self.files_read: set = set()
    
    def calibrate(
        self, 
        raw_confidence: float,
        factors: ConfidenceFactors
    ) -> float:
        """
        Calibrate confidence based on multiple factors.
        Returns adjusted confidence score.
        """
        # Calculate weighted score
        weighted_score = sum(
            getattr(factors, factor) * weight
            for factor, weight in self.WEIGHTS.items()
        )
        
        # Combine with raw confidence
        combined = (raw_confidence * 0.4) + (weighted_score * 0.6)
        
        # Apply session adjustments
        if self.session_errors > 3:
            combined *= 0.8  # Reduce if many errors in session
        elif self.session_errors > 1:
            combined *= 0.9
        
        return min(max(combined, 0.0), 1.0)
    
    def record_file_read(self, path: str):
        """Record that a file was read"""
        self.files_read.add(path)
    
    def record_error(self):
        """Record an error in session"""
        self.session_errors += 1
    
    def get_file_familiarity(self, paths: List[str]) -> float:
        """Calculate familiarity with files to be modified"""
        if not paths:
            return 0.5
        
        read_count = sum(1 for p in paths if p in self.files_read)
        return read_count / len(paths)
    
    def assess_complexity_match(
        self, 
        task_complexity: str, 
        approach_complexity: str
    ) -> float:
        """
        Assess if approach matches task complexity.
        
        Good match: Simple approach for simple task, thorough for complex
        Bad match: Simple approach for complex task
        """
        complexity_levels = {'low': 1, 'medium': 2, 'high': 3, 'very_high': 4}
        
        task_level = complexity_levels.get(task_complexity, 2)
        approach_level = complexity_levels.get(approach_complexity, 2)
        
        # Ideal: approach >= task
        if approach_level >= task_level:
            return 1.0
        elif approach_level == task_level - 1:
            return 0.7
        else:
            return 0.4
    
    def get_recommendation(self, confidence: float) -> Dict:
        """Get recommendation based on confidence"""
        if confidence >= 0.90:
            return {
                'action': 'proceed',
                'message': 'High confidence - safe to proceed'
            }
        elif confidence >= 0.75:
            return {
                'action': 'proceed_with_caution',
                'message': 'Good confidence - proceed with extra verification'
            }
        elif confidence >= 0.60:
            return {
                'action': 'additional_verification',
                'message': 'Medium confidence - recommend additional checks'
            }
        elif confidence >= 0.50:
            return {
                'action': 'reconsider',
                'message': 'Low confidence - consider alternative approach'
            }
        else:
            return {
                'action': 'stop',
                'message': 'Very low confidence - do not proceed'
            }


# ============================================
# 3. ERROR PATTERN RECOGNIZER
# ============================================

@dataclass
class ErrorPattern:
    """Recognized error pattern with solution"""
    pattern_id: str
    error_type: str
    pattern_regex: str
    description: str
    solution: str
    prevention: str
    occurrences: int = 0


class ErrorPatternRecognizer:
    """
    Recognizes error patterns and suggests solutions.
    Learns from errors in session.
    """
    
    KNOWN_PATTERNS = [
        ErrorPattern(
            pattern_id="py_syntax_indent",
            error_type="syntax",
            pattern_regex=r"IndentationError|unexpected indent|expected an indented",
            description="Python indentation error",
            solution="Check and fix indentation (use spaces, not tabs)",
            prevention="Use consistent 4-space indentation"
        ),
        ErrorPattern(
            pattern_id="py_import_missing",
            error_type="import",
            pattern_regex=r"ModuleNotFoundError|No module named|ImportError",
            description="Missing Python module",
            solution="Install the missing module with pip",
            prevention="Check requirements.txt before using imports"
        ),
        ErrorPattern(
            pattern_id="py_name_undefined",
            error_type="runtime",
            pattern_regex=r"NameError: name '(\w+)' is not defined",
            description="Undefined variable or function",
            solution="Define the variable/function before use",
            prevention="Read file first to understand existing definitions"
        ),
        ErrorPattern(
            pattern_id="file_not_found",
            error_type="io",
            pattern_regex=r"FileNotFoundError|No such file or directory",
            description="File or directory not found",
            solution="Create the file/directory or fix the path",
            prevention="Verify paths exist before operations"
        ),
        ErrorPattern(
            pattern_id="json_invalid",
            error_type="syntax",
            pattern_regex=r"JSONDecodeError|Invalid JSON",
            description="Invalid JSON syntax",
            solution="Fix JSON syntax (check commas, quotes, brackets)",
            prevention="Validate JSON before writing"
        ),
        ErrorPattern(
            pattern_id="edit_text_not_found",
            error_type="edit",
            pattern_regex=r"old_?text not found|text.*not found in file",
            description="Edit target text not found",
            solution="Read the file first to get exact text",
            prevention="Always read file before editing"
        ),
        ErrorPattern(
            pattern_id="type_error",
            error_type="runtime",
            pattern_regex=r"TypeError:.*(argument|operand|expected)",
            description="Type mismatch in operation",
            solution="Check and convert types appropriately",
            prevention="Use type hints and validation"
        ),
        ErrorPattern(
            pattern_id="permission_denied",
            error_type="io",
            pattern_regex=r"PermissionError|Permission denied",
            description="File permission error",
            solution="Check file permissions",
            prevention="Work within allowed directories"
        ),
    ]
    
    def __init__(self):
        self.patterns = self.KNOWN_PATTERNS.copy()
        self.session_errors: List[Dict] = []
        self.learned_patterns: List[ErrorPattern] = []
    
    def recognize(self, error: str) -> Optional[ErrorPattern]:
        """
        Recognize error pattern and return solution.
        """
        for pattern in self.patterns:
            if re.search(pattern.pattern_regex, error, re.IGNORECASE):
                pattern.occurrences += 1
                return pattern
        
        # Check learned patterns
        for pattern in self.learned_patterns:
            if re.search(pattern.pattern_regex, error, re.IGNORECASE):
                pattern.occurrences += 1
                return pattern
        
        return None
    
    def record_error(self, error: str, context: Dict = None):
        """Record error for learning"""
        self.session_errors.append({
            'error': error,
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'pattern': self.recognize(error)
        })
    
    def get_prevention_tips(self, recent_errors: int = 5) -> List[str]:
        """Get prevention tips based on recent errors"""
        tips = set()
        
        for error_record in self.session_errors[-recent_errors:]:
            pattern = error_record.get('pattern')
            if pattern:
                tips.add(pattern.prevention)
        
        return list(tips)
    
    def get_common_errors(self) -> List[Tuple[str, int]]:
        """Get most common error types in session"""
        error_counts: Dict[str, int] = {}
        
        for pattern in self.patterns + self.learned_patterns:
            if pattern.occurrences > 0:
                error_counts[pattern.description] = pattern.occurrences
        
        return sorted(error_counts.items(), key=lambda x: x[1], reverse=True)


# ============================================
# 4. CODE QUALITY SCORER
# ============================================

@dataclass
class QualityScore:
    """Code quality score breakdown"""
    overall: float
    syntax: float
    structure: float
    naming: float
    complexity: float
    documentation: float
    issues: List[str]
    suggestions: List[str]


class CodeQualityScorer:
    """
    Scores code quality before and after changes.
    Ensures we don't degrade code quality.
    """
    
    def score_python(self, code: str) -> QualityScore:
        """Score Python code quality"""
        issues = []
        suggestions = []
        scores = {
            'syntax': 1.0,
            'structure': 0.7,
            'naming': 0.7,
            'complexity': 0.7,
            'documentation': 0.5
        }
        
        # Syntax check
        try:
            import ast
            tree = ast.parse(code)
        except SyntaxError as e:
            issues.append(f"Syntax error: {e.msg}")
            return QualityScore(
                overall=0.0,
                syntax=0.0,
                structure=0.0,
                naming=0.0,
                complexity=0.0,
                documentation=0.0,
                issues=issues,
                suggestions=["Fix syntax errors first"]
            )
        
        # Analyze structure
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        # Check function length
        long_functions = []
        for func in functions:
            lines = func.end_lineno - func.lineno if hasattr(func, 'end_lineno') else 50
            if lines > 50:
                long_functions.append(func.name)
        
        if long_functions:
            issues.append(f"Long functions: {', '.join(long_functions)}")
            suggestions.append("Consider breaking down long functions")
            scores['structure'] -= 0.1 * len(long_functions)
        
        # Check naming conventions
        bad_names = []
        for func in functions:
            if not re.match(r'^[a-z_][a-z0-9_]*$', func.name):
                if not func.name.startswith('_'):
                    bad_names.append(func.name)
        
        for cls in classes:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', cls.name):
                bad_names.append(cls.name)
        
        if bad_names:
            issues.append(f"Non-conventional names: {', '.join(bad_names[:5])}")
            suggestions.append("Use snake_case for functions, PascalCase for classes")
            scores['naming'] -= 0.1 * len(bad_names)
        
        # Check documentation
        documented_funcs = sum(1 for f in functions if ast.get_docstring(f))
        if functions:
            doc_ratio = documented_funcs / len(functions)
            scores['documentation'] = doc_ratio
            if doc_ratio < 0.5:
                suggestions.append("Add docstrings to functions")
        
        # Check complexity (simple heuristic)
        nested_depth = self._max_nesting_depth(code)
        if nested_depth > 4:
            issues.append(f"Deep nesting detected (depth: {nested_depth})")
            suggestions.append("Reduce nesting with early returns or extraction")
            scores['complexity'] -= 0.1 * (nested_depth - 4)
        
        # Calculate overall
        overall = sum(scores.values()) / len(scores)
        
        return QualityScore(
            overall=max(overall, 0.0),
            syntax=scores['syntax'],
            structure=max(scores['structure'], 0.0),
            naming=max(scores['naming'], 0.0),
            complexity=max(scores['complexity'], 0.0),
            documentation=scores['documentation'],
            issues=issues,
            suggestions=suggestions
        )
    
    def _max_nesting_depth(self, code: str) -> int:
        """Calculate maximum nesting depth"""
        max_depth = 0
        current_depth = 0
        
        for line in code.split('\n'):
            stripped = line.lstrip()
            if not stripped or stripped.startswith('#'):
                continue
            
            indent = len(line) - len(stripped)
            level = indent // 4
            
            if level > max_depth:
                max_depth = level
        
        return max_depth
    
    def compare_quality(
        self, 
        before: str, 
        after: str
    ) -> Dict:
        """
        Compare code quality before and after change.
        Returns degradation warnings if quality decreased.
        """
        before_score = self.score_python(before)
        after_score = self.score_python(after)
        
        degradations = []
        improvements = []
        
        for attr in ['syntax', 'structure', 'naming', 'complexity', 'documentation']:
            before_val = getattr(before_score, attr)
            after_val = getattr(after_score, attr)
            
            if after_val < before_val - 0.1:
                degradations.append(f"{attr}: {before_val:.2f} → {after_val:.2f}")
            elif after_val > before_val + 0.1:
                improvements.append(f"{attr}: {before_val:.2f} → {after_val:.2f}")
        
        return {
            'before_overall': before_score.overall,
            'after_overall': after_score.overall,
            'degradations': degradations,
            'improvements': improvements,
            'quality_maintained': len(degradations) == 0,
            'new_issues': after_score.issues
        }


# ============================================
# 5. ITERATIVE REFINEMENT ENGINE
# ============================================

@dataclass 
class RefinementIteration:
    """Single refinement iteration"""
    iteration: int
    issues_found: List[str]
    fixes_applied: List[str]
    quality_before: float
    quality_after: float
    success: bool


class IterativeRefinementEngine:
    """
    Iteratively refines code until quality target is met.
    
    Process:
    1. Assess current quality
    2. Identify issues
    3. Apply targeted fixes
    4. Re-assess quality
    5. Repeat until target or max iterations
    """
    
    def __init__(
        self, 
        quality_scorer: CodeQualityScorer,
        target_quality: float = 0.85,
        max_iterations: int = 5
    ):
        self.scorer = quality_scorer
        self.target_quality = target_quality
        self.max_iterations = max_iterations
        self.iterations: List[RefinementIteration] = []
    
    async def refine(
        self,
        code: str,
        language: str,
        llm_client,
        session_id: str = "refinement"
    ) -> Tuple[str, List[RefinementIteration]]:
        """
        Iteratively refine code to meet quality target.
        
        Returns:
            (refined_code, iterations_log)
        """
        current_code = code
        self.iterations = []
        
        for i in range(self.max_iterations):
            # Assess current quality
            if language == 'python':
                quality = self.scorer.score_python(current_code)
            else:
                # Skip refinement for unsupported languages
                break
            
            # Check if target met
            if quality.overall >= self.target_quality:
                self.iterations.append(RefinementIteration(
                    iteration=i,
                    issues_found=[],
                    fixes_applied=["Target quality achieved"],
                    quality_before=quality.overall,
                    quality_after=quality.overall,
                    success=True
                ))
                break
            
            # Get fixes for issues
            fixes = await self._get_fixes(
                current_code, 
                quality.issues, 
                quality.suggestions,
                llm_client,
                session_id
            )
            
            if not fixes:
                # No more fixes available
                self.iterations.append(RefinementIteration(
                    iteration=i,
                    issues_found=quality.issues,
                    fixes_applied=[],
                    quality_before=quality.overall,
                    quality_after=quality.overall,
                    success=False
                ))
                break
            
            # Apply fixes
            refined_code = fixes.get('refined_code', current_code)
            
            # Re-assess
            new_quality = self.scorer.score_python(refined_code)
            
            self.iterations.append(RefinementIteration(
                iteration=i,
                issues_found=quality.issues,
                fixes_applied=fixes.get('fixes_applied', []),
                quality_before=quality.overall,
                quality_after=new_quality.overall,
                success=new_quality.overall > quality.overall
            ))
            
            # Only keep if quality improved
            if new_quality.overall >= quality.overall:
                current_code = refined_code
            else:
                # Quality degraded, stop
                break
        
        return current_code, self.iterations
    
    async def _get_fixes(
        self, 
        code: str, 
        issues: List[str],
        suggestions: List[str],
        llm_client,
        session_id: str
    ) -> Dict:
        """Get fixes for identified issues using LLM"""
        if not issues and not suggestions:
            return {}
        
        prompt = f"""
Fix the following issues in this code:

ISSUES:
{chr(10).join([f'- {i}' for i in issues])}

SUGGESTIONS:
{chr(10).join([f'- {s}' for s in suggestions])}

CODE:
```python
{code[:3000]}  # Truncated
```

Provide the fixed code only, no explanations.
"""
        
        try:
            messages = [{"role": "user", "content": prompt}]
            result = await llm_client.chat_stream(messages, session_id)
            response = result.get('response', '')
            
            # Extract code from response
            code_match = re.search(r'```python\n(.+?)```', response, re.DOTALL)
            if code_match:
                return {
                    'refined_code': code_match.group(1),
                    'fixes_applied': issues[:3]  # Top 3 issues
                }
            
            # If no code block, try the whole response
            if 'def ' in response or 'class ' in response:
                return {
                    'refined_code': response,
                    'fixes_applied': issues[:3]
                }
        
        except Exception:
            pass
        
        return {}
    
    def get_refinement_summary(self) -> Dict:
        """Get summary of refinement process"""
        if not self.iterations:
            return {'iterations': 0, 'success': False}
        
        initial_quality = self.iterations[0].quality_before
        final_quality = self.iterations[-1].quality_after
        
        return {
            'iterations': len(self.iterations),
            'initial_quality': initial_quality,
            'final_quality': final_quality,
            'improvement': final_quality - initial_quality,
            'target_met': final_quality >= self.target_quality,
            'total_issues_fixed': sum(
                len(i.fixes_applied) for i in self.iterations if i.success
            )
        }


# ============================================
# INTEGRATION HELPERS
# ============================================

def create_accuracy_suite(workspace_root: str) -> Dict:
    """
    Create complete accuracy enhancement suite.
    
    Returns dict of all accuracy systems ready for integration.
    """
    return {
        'validator': PreExecutionValidator(workspace_root),
        'calibrator': ConfidenceCalibrator(),
        'error_recognizer': ErrorPatternRecognizer(),
        'quality_scorer': CodeQualityScorer(),
        'refinement_engine': IterativeRefinementEngine(
            CodeQualityScorer(),
            target_quality=0.85,
            max_iterations=5
        )
    }


async def validate_and_execute(
    action: Dict,
    executor,
    accuracy_suite: Dict
) -> Dict:
    """
    Validate action before execution and handle errors.
    
    This is the main integration point for accuracy systems.
    """
    validator = accuracy_suite['validator']
    error_recognizer = accuracy_suite['error_recognizer']
    
    # Pre-execution validation
    validation = validator.validate_action(action)
    
    if not validation.valid:
        return {
            'success': False,
            'blocked': True,
            'reason': 'Pre-execution validation failed',
            'issues': validation.blocking_issues,
            'suggestions': validation.suggestions
        }
    
    # Execute
    try:
        result = executor.execute_tool(
            action.get('tool', action.get('action', '')),
            action.get('args', {})
        )
        
        if not result.get('success'):
            # Record and analyze error
            error = result.get('error', 'Unknown error')
            error_recognizer.record_error(error, action)
            
            pattern = error_recognizer.recognize(error)
            if pattern:
                result['error_pattern'] = pattern.pattern_id
                result['suggested_solution'] = pattern.solution
                result['prevention_tip'] = pattern.prevention
        
        return result
    
    except Exception as e:
        error_recognizer.record_error(str(e), action)
        return {
            'success': False,
            'error': str(e),
            'prevention_tips': error_recognizer.get_prevention_tips()
        }
