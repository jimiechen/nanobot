"""Skill executor for running skill scripts directly without LLM."""

import asyncio
import sys
from pathlib import Path
from typing import Any

from loguru import logger


class SkillExecutor:
    """直接执行 skill 脚本，不经过 LLM"""

    def __init__(self, workspace: Path, skills_root: Path | None = None):
        self.workspace = workspace
        # skills_root is the root directory containing skills/nanobot
        # If not provided, assume skills are in the parent of workspace
        if skills_root:
            self.skills_dir = skills_root / "skills" / "nanobot"
        else:
            # Try to find skills directory - check parent of workspace first
            parent_skills = workspace.parent / "skills" / "nanobot"
            if parent_skills.exists():
                self.skills_dir = parent_skills
            else:
                # Fallback to workspace/skills
                self.skills_dir = workspace / "skills" / "nanobot"

    async def execute(
        self,
        skill_name: str,
        script: str,
        args: list[str] | None = None,
        timeout: int = 300
    ) -> dict[str, Any]:
        """
        执行 skill 脚本

        Args:
            skill_name: Skill 名称
            script: 脚本路径（相对于 skill 目录）
            args: 脚本参数
            timeout: 执行超时时间（秒）

        Returns:
            {
                "success": bool,
                "stdout": str,
                "stderr": str,
                "returncode": int
            }
        """
        script_path = self.skills_dir / skill_name / script

        if not script_path.exists():
            logger.error("Script not found: {}", script_path)
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Script not found: {script_path}",
                "returncode": -1
            }

        cmd = [sys.executable, str(script_path)] + (args or [])

        logger.info("Executing skill script: {}", " ".join(cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace)
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )

            stdout_str = stdout.decode('utf-8', errors='ignore')
            stderr_str = stderr.decode('utf-8', errors='ignore')

            success = proc.returncode == 0

            if success:
                logger.info("Skill script executed successfully")
            else:
                logger.error("Skill script failed with code {}: {}",
                           proc.returncode, stderr_str)

            return {
                "success": success,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "returncode": proc.returncode
            }

        except asyncio.TimeoutError:
            logger.error("Skill script execution timed out after {}s", timeout)
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout}s",
                "returncode": -1
            }
        except Exception as e:
            logger.error("Skill script execution failed: {}", e)
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
