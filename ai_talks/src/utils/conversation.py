from random import randrange

import streamlit as st
from openai.error import InvalidRequestError, OpenAIError
from requests.exceptions import TooManyRedirects
from streamlit_chat import message

from .agi import phind
from .agi.bard import BardChat
from .agi.chat_gpt import create_gpt_completion
from .stt import show_voice_input
from .tts import show_audio_player

phind.cf_clearance = st.secrets.api_credentials.phind_cf_clearance
phind.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"  # noqa: E501


def clear_chat() -> None:
    st.session_state.generated = []
    st.session_state.past = []
    st.session_state.messages = []
    st.session_state.user_text = ""
    st.session_state.seed = randrange(10**8)  # noqa: S311


def show_text_input() -> None:
    st.text_area(label=st.session_state.locale.chat_placeholder, value=st.session_state.user_text, key="user_text")


def get_user_input():
    match st.session_state.input_kind:
        case st.session_state.locale.input_kind_1:
            show_text_input()
        case st.session_state.locale.input_kind_2:
            show_voice_input()
        case _:
            show_text_input()


def show_chat_buttons() -> None:
    b0, b1, b2 = st.columns(3)
    with b0, b1, b2:
        b0.button(label=st.session_state.locale.chat_run_btn)
        b1.button(label=st.session_state.locale.chat_clear_btn, on_click=clear_chat)
        b2.download_button(
            label=st.session_state.locale.chat_save_btn,
            data="\n".join([str(d) for d in st.session_state.messages[1:]]),
            file_name="ai-talks-chat.json",
            mime="application/json",
        )


def show_chat(ai_content: str, user_text: str) -> None:
    if ai_content not in st.session_state.generated:
        # store the ai content
        st.session_state.past.append(user_text)
        st.session_state.generated.append(ai_content)
    if st.session_state.generated:
        for i in range(len(st.session_state.generated)):
            message(st.session_state.past[i], is_user=True, key=str(i) + "_user", seed=st.session_state.seed)
            message("", key=str(i), seed=st.session_state.seed)
            st.markdown(st.session_state.generated[i])


def show_gpt_conversation() -> None:
    try:
        completion = create_gpt_completion(st.session_state.model, st.session_state.messages)
        ai_content = completion.get("choices")[0].get("message").get("content")
        st.session_state.messages.append({"role": "assistant", "content": ai_content})
        if ai_content:
            show_chat(ai_content, st.session_state.user_text)
            st.divider()
            # show_audio_player(ai_content)
    except InvalidRequestError as err:
        if err.code == "context_length_exceeded":
            st.session_state.messages.pop(1)
            if len(st.session_state.messages) == 1:
                st.session_state.user_text = ""
            show_conversation()
        else:
            st.error(err)
    except (OpenAIError, UnboundLocalError) as err:
        st.error(err)


def show_bard_conversation() -> None:
    try:
        bard = BardChat(st.secrets.api_credentials.bard_session)
        ai_content = bard.ask(st.session_state.user_text)
        st.warning(ai_content.get("content"))
    except (TooManyRedirects, AttributeError) as err:
        st.error(err)


def phind_get_answer(question: str):
    try:
        result = phind.Completion.create(
            model="gpt-4",
            prompt=question,
            results=phind.Search.create(question, actual_search=True),
            creative=False,
            detailed=False,
            code_context=""
        )
        st.markdown(result.completion.choices[0].text)
    except Exception as e:
        st.error(e)


def show_conversation() -> None:
    if st.session_state.messages:
        st.session_state.messages.append({"role": "user", "content": st.session_state.user_text})
    else:
        ai_role = f"{st.session_state.locale.ai_role_prefix} {st.session_state.role}. {st.session_state.locale.ai_role_postfix}"  # NOQA: E501
        st.session_state.messages = [
            {"role": "system", "content": ai_role},
            {"role": "user", "content": st.session_state.user_text},
        ]
    if st.session_state.model == "bard":
        show_bard_conversation()
    elif st.session_state.model == "phind-gpt-4":
        phind_get_answer(st.session_state.user_text)
    else:
        show_gpt_conversation()
